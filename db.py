import sqlite3

import pypika


class DatabaseNative:
    def __init__(self, db_path, password):
        self.conn = sqlite3.connect(db_path)
        if password:
            raise NotImplementedError

    def execute(self, script):
        cursor = self.conn.cursor()
        res = cursor.executescript(script)

        self.conn.commit()
        return res

    def vacuum(self):
        cursor = self.conn.cursor()
        cursor.execute("VACUUM")

    # def create(self, table, data):
    #     cursor = self.conn.cursor()
    #     cursor.execute(
    #         f"INSERT INTO ? ()",
    #     )  # will fail not exist
    #     return

    # def read(self, table, criteria):
    #     if table not in self.db_properties:
    #         raise ValueError(f"Table '{table}' does not exist.")

    #     cursor.execute(
    #         f"SELECT ? ()",
    #     )  # will fail not exist
    #     return records

    # def update(self, table, criteria, new_data):
    #     if table not in self.db_properties:
    #         raise ValueError(f"Table '{table}' does not exist.")

    #     updated_count = 0
    #     cursor.execute(
    #         f"UPDATE ? ()",
    #     )  # will fail not exist
    #     return updated_count

    # def delete(self, table, criteria):
    #     if table not in self.db_properties:
    #         raise ValueError(f"Table '{table}' does not exist.")

    #     to_delete = []
    #     cursor.execute(
    #         f"DELETE FROM ? WHERE user_id = ?",
    #     )  # will fail not exist
    #     return len(to_delete)

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

    def fields(self):
        return pypika.Table(self.table_name)


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

    def create(self, user_id: str, permisision: str, auth_method: str):
        # TODO: consider inserting with PyPika
        # .into().columns.insert()
        self.db.execute(
            f"""
INSERT INTO `users` (`user_id`, `permissions`, `auth_method`)
VALUES ({user_id}, {permisision}, {auth_method});
"""
        )

    # def query(
    #     self,
    #     user_id: str | None,
    #     permisision: str | None,
    #     auth_method: str | None,
    #     fields: tuple[str, ...] = ("user_id", "permissions", "auth_method"),
    # ):
    #     return self.query_cond(
    #         user_id and f"= {user_id}",
    #         permisision and f"= {permisision}",
    #         auth_method and f"= {auth_method}",
    #         fields,
    #     )  # pass None or "= <value>"

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
