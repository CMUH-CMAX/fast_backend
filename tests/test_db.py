import os
import sys
import unittest

# A workaround trick for importing source modules. Just fine for testing.
sys.path.append(os.path.abspath("."))

# pylint: disable = wrong-import-position
from db import BaseTableDatabase, DatabaseNative


class SampleUserDatabase(BaseTableDatabase):
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

    def create_bulk(self, entries):
        return self.create_bulk_from(
            entries, ("permissions", "auth_method"), ("user_id",)
        )

    def query(
        self,
        criterion,
        select_fields: tuple[str, ...] = ("user_id", "permissions", "auth_method"),
    ):
        return super().query(criterion, select_fields)

    def query_value(
        self,
        entry,
        select_fields: tuple[str, ...] = ("user_id", "permissions", "auth_method"),
    ):
        return super().query_value(entry, select_fields)


# TODO: use `self.assert*`
# pylint: disable = invalid-name, missing-function-docstring
class BasicDatabaseTestCase(unittest.TestCase):
    """
    Tests overriding base table with sample schema.
    """

    def setUp(self):
        os.makedirs(".test", exist_ok=True)
        with open(".test/_test_db_test.db", "w", encoding="utf-8"):
            # truncate test db file
            pass

        self.db = DatabaseNative(".test/_test_db_test.db")
        self.udb = SampleUserDatabase(self.db)

    def testCreateTable(self):
        self.db.execute("DROP TABLE users")

        self.udb = SampleUserDatabase(self.db)
        self.db.execute("SELECT * FROM users")  # will error if not exist

    def testCreate(self):
        self.db.execute("DELETE FROM users")

        users = [
            {"permissions": 0, "auth_method": "google"},
            {"permissions": 3, "auth_method": "facebook"},
            {"permissions": 2, "auth_method": "email"},
        ]

        (id1,) = self.udb.create(users[0])
        (id2,), (id3,) = self.udb.create(users[1:])

        assert self.db.execute("select * from users") == [
            (id1, 0, "google"),
            (id2, 3, "facebook"),
            (id3, 2, "email"),
        ]

    def testQueryValue(self):
        self.db.execute("DELETE FROM users")

        users = [
            {"permissions": 0, "auth_method": "google"},
            {"permissions": 3, "auth_method": "facebook"},
            {"permissions": 3, "auth_method": "facebook"},
            {"permissions": 2, "auth_method": "email"},
            {"permissions": 1, "auth_method": "facebook"},
            {"permissions": 2, "auth_method": "google"},
            {"permissions": 5, "auth_method": "admin"},
        ]

        self.udb.create(users)

        assert self.udb.query_value({}) == [
            (1, 0, "google"),
            (2, 3, "facebook"),
            (3, 3, "facebook"),
            (4, 2, "email"),
            (5, 1, "facebook"),
            (6, 2, "google"),
            (7, 5, "admin"),
        ]

        # ("user_id", "permissions", "auth_method")
        assert self.udb.query_value({"user_id": 3}, ("permissions", "auth_method")) == [
            (3, "facebook")
        ]

        assert self.udb.query_value(
            {"auth_method": "facebook"}, ("user_id", "permissions", "auth_method")
        ) == [
            (2, 3, "facebook"),
            (3, 3, "facebook"),
            (5, 1, "facebook"),
        ]

        assert self.udb.query_value(
            {"permissions": 3, "auth_method": "facebook"}, ("user_id",)
        ) == [
            (2,),
            (3,),
        ]

    def testQuery(self):
        self.db.execute("DELETE FROM users")

        users = [
            {"permissions": 0, "auth_method": "google"},
            {"permissions": 3, "auth_method": "facebook"},
            {"permissions": 3, "auth_method": "facebook"},
            {"permissions": 2, "auth_method": "email"},
            {"permissions": 1, "auth_method": "facebook"},
            {"permissions": 2, "auth_method": "google"},
            {"permissions": 5, "auth_method": "admin"},
        ]

        self.udb.create(users)

        table, empty_criterion = self.udb.criterion_selector()

        assert self.udb.query(empty_criterion) == [
            (1, 0, "google"),
            (2, 3, "facebook"),
            (3, 3, "facebook"),
            (4, 2, "email"),
            (5, 1, "facebook"),
            (6, 2, "google"),
            (7, 5, "admin"),
        ]

        assert self.udb.query(table["auth_method"] == "google") == [
            (1, 0, "google"),
            (6, 2, "google"),
        ]

        assert self.udb.query(table.permissions > 3) == [
            (7, 5, "admin"),
        ]

        assert self.udb.query(
            # only '&', '|' (rather than 'and', 'or') will work
            # note that parenthesis matters
            (table.permissions > 1) & (table.auth_method == "facebook"),
            ("user_id", "permissions"),
        ) == [
            (2, 3),
            (3, 3),
        ]

    def testUpdate(self):
        self.db.execute("DELETE FROM users")

        users = [
            {"permissions": 0, "auth_method": "google"},
            {"permissions": 3, "auth_method": "facebook"},
            {"permissions": 3, "auth_method": "facebook"},
            {"permissions": 2, "auth_method": "email"},
            {"permissions": 1, "auth_method": "facebook"},
            {"permissions": 2, "auth_method": "google"},
            {"permissions": 5, "auth_method": "admin"},
        ]

        self.udb.create(users)

        table, empty_criterion = self.udb.criterion_selector()

        self.udb.update(table.user_id == 3, {"permissions": 1})
        assert self.udb.query(empty_criterion) == [
            (1, 0, "google"),
            (2, 3, "facebook"),
            (3, 1, "facebook"),
            (4, 2, "email"),
            (5, 1, "facebook"),
            (6, 2, "google"),
            (7, 5, "admin"),
        ]

        self.udb.update(table.auth_method == "google", {"auth_method": "gmail"})
        assert self.udb.query(empty_criterion) == [
            (1, 0, "gmail"),
            (2, 3, "facebook"),
            (3, 1, "facebook"),
            (4, 2, "email"),
            (5, 1, "facebook"),
            (6, 2, "gmail"),
            (7, 5, "admin"),
        ]

        self.udb.update(
            table.permissions == 0, {"permissions": 5, "auth_method": "admin"}
        )
        assert self.udb.query(empty_criterion) == [
            (1, 5, "admin"),
            (2, 3, "facebook"),
            (3, 1, "facebook"),
            (4, 2, "email"),
            (5, 1, "facebook"),
            (6, 2, "gmail"),
            (7, 5, "admin"),
        ]

        self.udb.update(
            (table.permissions > 2) & (table.auth_method != "admin"),
            {"permissions": 2},
        )
        assert self.udb.query(empty_criterion) == [
            (1, 5, "admin"),
            (2, 2, "facebook"),
            (3, 1, "facebook"),
            (4, 2, "email"),
            (5, 1, "facebook"),
            (6, 2, "gmail"),
            (7, 5, "admin"),
        ]

    def testDelete(self):
        self.db.execute("DELETE FROM users")

        users = [
            {"permissions": 0, "auth_method": "google"},
            {"permissions": 3, "auth_method": "facebook"},
            {"permissions": 3, "auth_method": "facebook"},
            {"permissions": 2, "auth_method": "email"},
            {"permissions": 1, "auth_method": "facebook"},
            {"permissions": 2, "auth_method": "google"},
            {"permissions": 5, "auth_method": "admin"},
        ]

        self.udb.create(users)

        table, empty_criterion = self.udb.criterion_selector()

        self.udb.delete(table.permissions == 0)
        assert self.udb.query(empty_criterion) == [
            (2, 3, "facebook"),
            (3, 3, "facebook"),
            (4, 2, "email"),
            (5, 1, "facebook"),
            (6, 2, "google"),
            (7, 5, "admin"),
        ]

        self.udb.delete(table.auth_method.isin(["google", "admin"]))
        assert self.udb.query(empty_criterion) == [
            (2, 3, "facebook"),
            (3, 3, "facebook"),
            (4, 2, "email"),
            (5, 1, "facebook"),
        ]

        self.udb.delete(table.permissions.between(1, 2))
        assert self.udb.query(empty_criterion) == [
            (2, 3, "facebook"),
            (3, 3, "facebook"),
        ]

        self.udb.delete(empty_criterion)
        assert self.udb.query(empty_criterion) == []

    def tearDown(self):
        del self.udb
        del self.db

        os.remove(".test/_test_db_test.db")


if __name__ == "__main__":
    unittest.main()
