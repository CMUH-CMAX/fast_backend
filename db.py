from abc import ABC, abstractmethod
from collections.abc import Sequence
import logging
import sqlite3

import pypika


logger = logging.getLogger(__name__)


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

    def __init__(self, table_name: str, db: DatabaseNative) -> None:
        self.db = db
        self.table_name = table_name

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
        select_fields: tuple[str, ...],
    ):
        """
        Query table for entries that satisfies `criterion`, selecting `select_fields`.
        Override this method for default `select_fields`.
        """
        query = (
            pypika.Query.from_(self.table_name).select(*select_fields).where(criterion)
        )
        res = self.db.execute(str(query))
        return res

    def query_value(
        self,
        entry,
        select_fields: tuple[str, ...],
    ):
        """
        Query table for entries that have fields specified in `entry`, selecting `select_fields`.
        Override this method for default `select_fields`.
        """

        table, criterion = self.criterion_selector()
        for fd, fval in entry.items():
            criterion = criterion & (getattr(table, fd) == fval)

        return self.query(criterion, select_fields)

    def read(self, *args, **kwargs):
        """
        Alias of `query`.
        """
        return self.query(*args, **kwargs)

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
        super().__init__("users", db)

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

    def query(
        self,
        criterion: pypika.terms.Criterion,
        select_fields: tuple[str, ...] = (
            "user_id",
            "username",
            "password",
            "permission",
            "auth_method",
        ),
    ):
        return super().query(criterion, select_fields)

    def query_value(
        self,
        entry,
        select_fields: tuple[str, ...] = (
            "user_id",
            "username",
            "password",
            "permission",
            "auth_method",
        ),
    ):
        return super().query_value(entry, select_fields)


class SymptomDatabase(BaseTableDatabase):
    """
    The database (table) for symptoms.
    """

    def __init__(self, db: DatabaseNative) -> None:
        super().__init__("symptoms", db)

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

    def query(
        self,
        criterion: pypika.terms.Criterion,
        select_fields: tuple[str, ...] = ("symptoms_id", "name", "academic", "visit"),
    ):
        return super().query(criterion, select_fields)

    def query_value(
        self,
        entry,
        select_fields: tuple[str, ...] = ("symptoms_id", "name", "academic", "visit"),
    ):
        return super().query_value(entry, select_fields)
