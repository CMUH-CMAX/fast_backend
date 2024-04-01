from abc import ABC, abstractmethod
import base64
import binascii
from collections.abc import Callable, Collection, Mapping, Sequence
import json
import logging
import sqlite3
from types import MappingProxyType

import bcrypt
import pypika  # type: ignore
import pypika.terms


logger = logging.getLogger(__name__)

DB_PROPERTY = {
    "users": {
        "columns": {
            "user_id": {"dtype": "int", "primary": True, "auto_increment": True},
            "username": {"dtype": "str"},
            "password": {"dtype": "str"},
            "permission": {"dtype": "int"},
            "auth_method": {"dtype": "str"},
        },
    },
    "symptoms": {
        "columns": {
            "symptoms_id": {"dtype": "int", "primary": True, "auto_increment": True},
            "name": {"dtype": "str"},
            "academic": {"dtype": "str"},
            "visit": {"dtype": "int"},
        },
    },
    "bulletins": {
        "columns": {
            "bulletin_id": {"dtype": "int", "primary": True, "auto_increment": True},
            "class": {"dtype": "str"},
            "user_id": {"dtype": "int"},
            "title": {"dtype": "str"},
            "content": {"dtype": "str"},
            "update_at": {"dtype": "str"},
            "create_at": {"dtype": "str"},
        },
    },
    "clinics": {
        "columns": {
            "clinic_id": {"dtype": "int", "primary": True, "auto_increment": True},
            "title": {"dtype": "str"},
            "address": {"dtype": "str"},
            "tel": {"dtype": "str"},
            "tags": {"dtype": "array"},
            "owner_id": {"dtype": "int"},
        },
    },
}


def gen_password_hash(password: str):
    hash_bytes = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return base64.b64encode(hash_bytes).decode()


def check_password_hash(password: str, hash_: bytes):
    try:
        hash_bytes = base64.b64decode(hash_)
    except binascii.Error:
        return False

    return bcrypt.checkpw(password.encode(), hash_bytes)


class TypeConvertField(pypika.Field):
    def __init__(self, *args, converter: Callable[..., str], **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.converter = converter

    # pylint: disable = arguments-differ
    def wrap_constant(self, val, *args):
        """
        (From Pypika) Used for wrapping raw inputs such as numbers in Criterions and Operator.
        Value is wrapped
        """

        if not (isinstance(val, pypika.terms.Node) or val is None):
            # Should be custom-typed constant
            try:
                return pypika.terms.ValueWrapper(self.converter(val))
            except ValueError:
                # pylint: disable = logging-fstring-interpolation
                logger.error(
                    f"Failed to convert custom type: {self.table=}, {self.name=}, {val=}"
                )

        return pypika.terms.Term.wrap_constant(val, *args)


class TypeConvertTable(pypika.Table):
    DTYPE_MAP = {
        "str": "TEXT",
        "int": "INTEGER",
        "array": "CUSTOM_ARRAY",
    }

    CONVERTER = {"array": json.dumps}

    def __init__(self, *args, prop: Mapping[str, Mapping[str, str]]):
        super().__init__(*args)
        self.prop = prop

    def field(self, name: str) -> TypeConvertField:
        dtype = self.prop[name]["dtype"]
        if (conv := self.CONVERTER.get(dtype, None)) is not None:
            return TypeConvertField(name, table=self, converter=conv)

        return super().field(name)


class ExtendedColumn(pypika.Column):
    """
    A column extended with custom attributes.
    Pypika has support for attributes ('nullable', 'default').
    """

    EXTRA_ATTRIB = (
        "primary",
        "auto_increment",
    )

    def __init__(self, *args, extra_attr: Mapping[str, Collection[str]], **kwargs):
        super().__init__(*args, **kwargs)
        self.extra_attr = extra_attr

    # pylint: disable=consider-using-f-string
    def get_sql(self, **kwargs) -> str:
        primary = self.extra_attr.get("primary", False)
        auto_increment = self.extra_attr.get("auto_increment", False)

        # SQLite only supports auto increment on primary key
        if auto_increment and not primary:
            raise SyntaxError(
                "Auto-increment column is required to be primary (for SQLite)"
            )

        extra_sql = "{primary}{auto_increment}".format(
            primary=(" PRIMARY KEY" if primary else ""),
            auto_increment=(" AUTOINCREMENT" if auto_increment else ""),
        )

        column_sql = "{super_stmt}{extra_stmt}".format(
            super_stmt=super().get_sql(**kwargs), extra_stmt=extra_sql
        )

        return column_sql

    @classmethod
    def compile_column(
        cls, name: str, prop: Mapping[str, Collection[str]]
    ) -> pypika.Column:
        """
        Create column from property map.
        """
        prop_super = dict(prop)

        # VARCHAR/TEXT: SQLite does not impose any length restrictions
        dtype = TypeConvertTable.DTYPE_MAP[str(prop_super.pop("dtype"))]

        extend_attrib = {}
        for pname in cls.EXTRA_ATTRIB:
            if pname in prop:
                extend_attrib[pname] = prop_super.pop(pname)

        return cls(name, dtype, extra_attr=extend_attrib, **prop_super)


class DatabaseNative:
    """
    Connection to native (SQLite) database.
    """

    def __init__(self, db_path, password=None):
        sqlite3.register_converter("CUSTOM_ARRAY", json.loads)  # convert array at read
        self.conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        if password is not None:
            raise NotImplementedError

    def execute(self, script, params=()):
        """
        Execute database script (in SQL), and return all values fetched.
        Parameters should be specified in `params`, wrapped in a list containing each item.
        """
        logger.debug("Executing '%s', with params %s", script, params)
        # self.conn.set_trace_callback(logger.error)

        cursor = self.conn.cursor()
        res = cursor.execute(script, params).fetchall()  # TODO: optimize fetch

        self.conn.commit()
        return res

    def vacuum(self):
        """
        Perform regular database maintenance.
        """
        cursor = self.conn.cursor()
        cursor.execute("VACUUM")

    def __del__(self):
        self.conn.close()


# TODO: operation field check
class BaseTableDatabase(ABC):
    """
    The database base type, representing a database table.
    Perform data operation through DatabaseNative.
    """

    def __init__(
        self, table_name: str, db: DatabaseNative, fields: Mapping[str, Collection[str]]
    ) -> None:
        self.db = db
        self.table_name = table_name
        self.fields = fields

        self.create_table()

    def create_table(self):
        """
        Create table with fields `self.fields`, if not previously exist.
        """

        columns = [
            ExtendedColumn.compile_column(name, prop)
            for name, prop in self.fields["columns"].items()
        ]

        query = pypika.Query.create_table(self.table_name).columns(*columns)
        self.db.execute(str(query))

    def criterion_selector(self) -> tuple[pypika.Table, pypika.terms.Criterion]:
        """
        Get default criterion selector.
        Return: field selector (table), empty criterion (*)
        See: tests/test_db.py
        """
        return (
            TypeConvertTable(self.table_name, prop=self.fields["columns"]),  # type: ignore
            pypika.terms.EmptyCriterion(),
        )

    def create(self, entry: dict[str, object] | Sequence[dict[str, object]]):
        """
        Create/insert table entry.
        Supports single entry creation (dict) and bulk creation (list[dict]).
        See: tests/test_db.py
        """
        if isinstance(entry, Sequence):
            return self.create_bulk(entry)

        res = self.create_bulk((entry,))

        # single entry, return single result
        return res[0]

    def convert_entry(self, dtype, value):
        if (conv := TypeConvertTable.CONVERTER.get(dtype, None)) is not None:
            return conv(value)

        return value

    def create_bulk_from(
        self,
        entries: Sequence[dict[str, object]],
        value_columns: tuple[str],
        return_columns: tuple[str],
    ):
        """
        Helper function of create_bulk. Bulk create entries with specified columns.
        """
        query = pypika.Query.into(self.table_name).columns(*value_columns)

        # We need return values, so no executemany()
        # query = query.insert([pypika.Parameter("?") for _ in value_columns])
        values: list[object] = []
        for entry in entries:
            query = query.insert([pypika.Parameter("?") for _ in value_columns])
            values.extend(
                self.convert_entry(
                    self.fields["columns"][name]["dtype"],  # type: ignore
                    entry[name],
                )
                for name in value_columns
            )

        # for entry in entries:
        #     query = query.insert(*map(entry.__getitem__, value_columns))

        # PyPika does not support SQLite 'RETURNING'
        # query = query.returning(*return_columns) # TODO
        returning_str = (
            " RETURNING(" + ", ".join(f"`{name}`" for name in return_columns) + ")"
            if len(return_columns) > 0
            else ""
        )

        # pylint: disable = consider-using-f-string
        query_str = "{query}{returning}".format(
            query=str(query), returning=returning_str
        )

        # return: auto & default fields
        res = self.db.execute(query_str, values)
        return res

    def query(
        self,
        criterion: pypika.terms.Criterion,
        select_fields: tuple[str, ...] = ("*",),
    ):
        """
        Query table for entries that satisfies `criterion`, selecting `select_fields`.
        """
        query = (
            pypika.Query.from_(self.table_name).select(*select_fields).where(criterion)
        )
        res = self.db.execute(str(query))
        return res

    def query_value(
        self,
        entry,
        select_fields: tuple[str, ...] = ("*",),
    ):
        """
        Query table for entries that have fields specified in `entry`, selecting `select_fields`.
        """

        table, criterion = self.criterion_selector()
        for fd, fval in entry.items():
            criterion = criterion & (getattr(table, fd) == fval)

        return self.query(criterion, select_fields)

    def update(self, criterion: pypika.terms.Criterion, entry: dict[str, str]):
        """
        Update table entries that satisfies `criterion`, which set their fields to `entry`.
        """
        query = pypika.Query.update(self.table_name).where(criterion)
        for fd, fval in entry.items():
            dtype = self.fields["columns"][fd]["dtype"]  # type: ignore
            cval = self.convert_entry(dtype, fval)
            query = query.set(fd, cval)

        self.db.execute(str(query))

    def delete(self, criterion: pypika.terms.Criterion):
        """
        Delete table entries that satisfies `criterion`.
        """
        query = pypika.Query.from_(self.table_name).where(criterion).delete()
        self.db.execute(str(query))

    @abstractmethod
    def create_bulk(self, entries: Sequence[dict[str, object]]):
        """
        Bulk create entry. Creation requires equal format of fields (for now), so
        override of this method is required.
        """
        raise NotImplementedError


class UserDatabase(BaseTableDatabase):
    """
    The database (table) for user identity.
    """

    def __init__(self, db: DatabaseNative) -> None:
        super().__init__("users", db, DB_PROPERTY["users"])

    def create_bulk(self, entries):
        return self.create_bulk_from(
            entries, ("username", "password", "permission", "auth_method"), ("user_id",)
        )


class SymptomDatabase(BaseTableDatabase):
    """
    The database (table) for symptoms.
    """

    def __init__(self, db: DatabaseNative) -> None:
        super().__init__("symptoms", db, DB_PROPERTY["symptoms"])

    def create_bulk(self, entries):
        return self.create_bulk_from(
            entries, ("name", "academic", "visit"), ("symptoms_id",)
        )


class BulletinDatabase(BaseTableDatabase):
    """
    The database (table) for bulletins.
    """

    def __init__(self, db: DatabaseNative) -> None:
        super().__init__("bulletins", db, DB_PROPERTY["bulletins"])

    def create_bulk(self, entries):
        return self.create_bulk_from(
            entries,
            ("class", "user_id", "title", "content", "update_at", "create_at"),
            ("bulletin_id",),
        )


class ClinicDatabase(BaseTableDatabase):
    """
    The database (table) for regional clinic informations.
    """

    def __init__(self, db: DatabaseNative) -> None:
        super().__init__("clinics", db, DB_PROPERTY["clinics"])

    def create_bulk(self, entries):
        return self.create_bulk_from(
            entries,
            ("name", "address", "contact", "owner_id"),
            ("clinic_id",),
        )


class MasterDatabase:
    def __init__(self, db_path: str) -> None:
        self.db = DatabaseNative(db_path)
        self.tables: dict[str, BaseTableDatabase] = {
            "users": UserDatabase(self.db),
            "symptoms": SymptomDatabase(self.db),
            "bulletins": BulletinDatabase(self.db),
            "clinics": ClinicDatabase(self.db),
        }

    def create(
        self, table_name: str, entry: dict[str, object] | Sequence[dict[str, object]]
    ):
        table = self.tables[table_name]
        return table.create(entry)

    def query(
        self,
        table_name: str,
        criterion: pypika.terms.Criterion,
        select_fields: tuple[str, ...] = ("*",),
    ):
        table = self.tables[table_name]
        return table.query(criterion, select_fields)  # type: ignore

    def query_value(
        self,
        table_name: str,
        entry,
        select_fields: tuple[str, ...] = ("*",),
    ):
        table = self.tables[table_name]
        return table.query_value(entry, select_fields)  # type: ignore

    def read(
        self,
        table_name: str,
        entry: Mapping[str, object] | None = MappingProxyType({}),
        select_fields=("*",),
    ):
        """
        Query entries with fields equal to `entry`, in key-value mapping.
        """
        table = self.tables[table_name]
        res = self.query_value(table_name, entry, select_fields)

        keys = table.fields if select_fields == ("*",) else select_fields
        return [dict(zip(keys, ent)) for ent in res]

    def update(
        self, table_name: str, criterion: pypika.terms.Criterion, entry: dict[str, str]
    ):
        table = self.tables[table_name]
        return table.update(criterion, entry)  # type: ignore

    def delete(self, table_name: str, criterion: pypika.terms.Criterion):
        table = self.tables[table_name]
        return table.delete(criterion)  # type: ignore

    def get_table(self, table_name: str):
        table = self.tables[table_name]
        return table
