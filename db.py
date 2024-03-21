import sqlite3

import pypika


class DatabaseNative:
    def __init__(self, db_path, password=None):
        self.conn = sqlite3.connect(db_path)
        if password is not None:
            raise NotImplementedError

    def execute(self, script):
        cursor = self.conn.cursor()
        res = cursor.executescript(script)

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


class UserDatabase(BaseTableDatabase):
    """
    The database (table) for user identity.
    """

    def __init__(self, db: DatabaseNative) -> None:
        super().__init__("users", db)

        # TODO: consider creating with PyPika
        self.db.execute(
            """
CREATE TABLE `users` (
  `user_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `permissions` VARCHAR(256),
  `auth_method` VARCHAR(16)
);
"""
        )

    def create_user(self, permisision: str, auth_method: str):
        query = (
            pypika.Query.into("users")
            .columns("permissions", "auth_method")
            .insert(permisision, auth_method)
        )

        self.db.execute(str(query))

        res = self.db.execute("select last_insert_rowid();")
        user_id = res.fetchone()
        return user_id

    def query_value(
        self,
        user_id: str | None,
        permisision: str | None,
        auth_method: str | None,
        fields: tuple[str, ...] = ("user_id", "permissions", "auth_method"),
    ):
        field, criterion = self.criterion_selector()

        if user_id is not None:
            criterion = criterion & (field.user_id == user_id)

        if permisision is not None:
            criterion = criterion & (field.permisision == permisision)

        if auth_method is not None:
            criterion = criterion & (field.auth_method == auth_method)

        return self.query(criterion, fields)

    def query(
        self,
        criterion: pypika.terms.Criterion,
        fields: tuple[str, ...] = ("user_id", "permissions", "auth_method"),
    ):
        query = pypika.Query.from_(self.table_name).select(*fields).where(criterion)
        res = self.db.execute(str(query))
        return res.fetchall()

    def update(self, criterion: pypika.terms.Criterion, data: dict[str, str]):
        for key in data:
            if data not in ("permissions", "auth_method"):
                raise ValueError(f"Update failed: invalid data key `{key}`")

        query = pypika.Query.update(self.table_name).where(criterion)
        for skey, sval in data.items():
            query = query.set(skey, sval)

        self.db.execute(str(query))

    def delete(self, criterion: pypika.terms.Criterion):
        query = pypika.Query.from_(self.table_name).where(criterion).delete()
        self.db.execute(str(query))
