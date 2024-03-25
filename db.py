from collections.abc import Sequence
import logging
import sqlite3

import pypika


logger = logging.getLogger(__name__)


class DatabaseNative:
    def __init__(self, db_path, password=None):
        self.conn = sqlite3.connect(db_path)
        if password is not None:
            raise NotImplementedError

    def execute(self, script):
        cursor = self.conn.cursor()
        res = cursor.execute(script).fetchall()  # TODO: optimize fetch

        logger.debug(script)

        self.conn.commit()
        return res

    def vacuum(self):
        cursor = self.conn.cursor()
        cursor.execute("VACUUM")

    def __del__(self):
        self.conn.close()


class BaseTableDatabase:
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
        See: UserDatabase.query
        """
        return pypika.Table(self.table_name), pypika.terms.EmptyCriterion()


# TODO: operation field check
class UserDatabase(BaseTableDatabase):
    """
    The database (table) for user identity.
    """

    def __init__(self, db: DatabaseNative) -> None:
        super().__init__("users", db)

        # TODO: consider creating with PyPika
        self.db.execute(
            """
CREATE TABLE IF NOT EXISTS `users` (
  `user_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `permissions` INTEGER,
  `auth_method` VARCHAR(16)
)
"""
        )

    def create(self, entry):
        if isinstance(entry, Sequence):
            return self.create_bulk(entry)
        else:
            res = self.create_bulk((entry,))

            # single entry, return single result
            return res[0]

    def create_bulk(self, entries):
        query = pypika.Query.into("users").columns("permissions", "auth_method")

        for entry in entries:
            query = query.insert(entry["permissions"], entry["auth_method"])

        # PyPika does not support SQLite 'RETURNING'
        # query = query.returning("user_id") # TODO
        query_str = str(query) + "RETURNING(`user_id`)"

        # return: auto & default fields
        res = self.db.execute(query_str)
        return res

    def query_value(
        self,
        entry,
        select_fields: tuple[str, ...] = ("user_id", "permissions", "auth_method"),
    ):
        table, criterion = self.criterion_selector()
        for fd, fval in entry.items():
            criterion = criterion & (getattr(table, fd) == fval)

        return self.query(criterion, select_fields)

    def query(
        self,
        criterion: pypika.terms.Criterion,
        fields: tuple[str, ...] = ("user_id", "permissions", "auth_method"),
    ):
        query = pypika.Query.from_(self.table_name).select(*fields).where(criterion)
        res = self.db.execute(str(query))
        return res

    def read(self, *args, **kwargs):
        """
        Alias of `query`.
        """
        return self.query(*args, **kwargs)

    def update(self, criterion: pypika.terms.Criterion, entry: dict[str, str]):
        query = pypika.Query.update(self.table_name).where(criterion)
        for fd, fval in entry.items():
            query = query.set(fd, fval)

        self.db.execute(str(query))

    def delete(self, criterion: pypika.terms.Criterion):
        query = pypika.Query.from_(self.table_name).where(criterion).delete()
        self.db.execute(str(query))
