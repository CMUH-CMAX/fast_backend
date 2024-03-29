from abc import ABC, abstractmethod
import base64
import binascii
from collections.abc import Sequence, Mapping
import logging
import sqlite3
from types import MappingProxyType

import bcrypt
import pypika  # type: ignore


logger = logging.getLogger(__name__)

DB_PROPERTY = {
    "users": {
        "user_id": {"dtype": "int", "auto_increment": True},
        "username": {"dtype": "str"},
        "password": {"dtype": "str"},
        "permission": {"dtype": "int"},
        "auth_method": {"dtype": "str"},
    },
    "symptoms": {
        "symptoms_id": {"dtype": "int", "auto_increment": True},
        "name": {"dtype": "str"},
        "academic": {"dtype": "str"},
        "visit": {"dtype": "int"},
    },
    "bulletins": {
        "bulletin_id": {"dtype": "int", "auto_increment": True},
        "class": {"dtype": "str"},
        "user_id": {"dtype": "int"},
        "title": {"dtype": "str"},
        "content": {"dtype": "str"},
        "update_at": {"dtype": "str"},
        "create_at": {"dtype": "str"},
    },
    "clinics": {
        "clinic_id": {"dtype": "int", "auto_increment": True},
        "title": {"dtype": "str"},
        "address": {"dtype": "str"},
        "tel": {"dtype": "str"},
        "tags": {"dtype": "array"},
        "owner_id": {"dtype": "int"},
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


class DatabaseNative:
    """
    Connection to native (SQLite) database.
    """

    def __init__(self, db_path, password=None):
        self.conn = sqlite3.connect(db_path)
        if password is not None:
            raise NotImplementedError

    def execute(self, script):
        """
        Execute database script (in SQL), and return all values fetched.
        """
        logger.debug(script)

        cursor = self.conn.cursor()
        res = cursor.execute(script).fetchall()  # TODO: optimize fetch

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
        self, table_name: str, db: DatabaseNative, fields: tuple[str, ...]
    ) -> None:
        self.db = db
        self.table_name = table_name
        self.fields = fields

    def criterion_selector(self) -> tuple[pypika.Table, pypika.terms.Criterion]:
        """
        Get default criterion selector.
        Return: field selector (table), empty criterion (*)
        See: tests/test_db.py
        """
        return pypika.Table(self.table_name), pypika.terms.EmptyCriterion()

    def create(self, entry: dict[str, object] | Sequence[dict[str, object]]):
        """
        Create/insert table entry.
        Supports single entry creation (dict) and bulk creation (list[dict]).
        See: tests/test_db.py
        """
        if isinstance(entry, Sequence):
            return self.create_bulk(entry)
        else:
            res = self.create_bulk((entry,))

            # single entry, return single result
            return res[0]

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

        for entry in entries:
            query = query.insert(*map(entry.__getitem__, value_columns))

        # PyPika does not support SQLite 'RETURNING'
        # query = query.returning(*return_columns) # TODO
        query_str = (
            str(query)
            + "RETURNING("
            + ", ".join(f"`{name}`" for name in return_columns)
            + ")"
        )

        # return: auto & default fields
        res = self.db.execute(query_str)
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
            query = query.set(fd, fval)

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
        super().__init__(
            "users",
            db,
            (
                "user_id",
                "username",
                "password",
                "permission",
                "auth_method",
            ),
        )

        # VARCHAR/TEXT: SQLite does not impose any length restrictions
        self.db.execute(
            """
CREATE TABLE IF NOT EXISTS `users` (
  `user_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `username` TEXT,
  `password` TEXT,
  `permission` INTEGER,
  `auth_method` TEXT
)
"""
        )

    def create_bulk(self, entries):
        return self.create_bulk_from(
            entries, ("username", "password", "permission", "auth_method"), ("user_id",)
        )


class SymptomDatabase(BaseTableDatabase):
    """
    The database (table) for symptoms.
    """

    def __init__(self, db: DatabaseNative) -> None:
        super().__init__("symptoms", db, ("symptoms_id", "name", "academic", "visit"))

        self.db.execute(
            """
CREATE TABLE IF NOT EXISTS `symptoms` (
  `symptoms_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` TEXT,
  `academic` TEXT,
  `visit` INTEGER
)
"""
        )

    def create_bulk(self, entries):
        return self.create_bulk_from(
            entries, ("name", "academic", "visit"), ("symptoms_id",)
        )


class BulletinDatabase(BaseTableDatabase):
    """
    The database (table) for bulletins.
    """

    def __init__(self, db: DatabaseNative) -> None:
        super().__init__(
            "bulletins",
            db,
            (
                "bulletin_id",
                "class",
                "user_id",
                "title",
                "content",
                "update_at",
                "create_at",
            ),
        )

        self.db.execute(
            """
CREATE TABLE IF NOT EXISTS `bulletins` (
  `bulletin_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `class` TEXT,
  `user_id` INTEGER,
  `title` TEXT,
  `content` TEXT,
  `update_at` TEXT,
  `create_at` TEXT
)
"""
        )

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
        super().__init__(
            "clinics",
            db,
            (
                "clinic_id",
                "name",
                "address",
                "contact",
                "owner_id",
            ),
        )

        self.db.execute(
            """
CREATE TABLE IF NOT EXISTS `clinics` (
  `clinic_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` TEXT,
  `address` TEXT,
  `contact` TEXT,
  `owner_id` INTEGER
)
"""
        )

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
