import json
import os
import random
import sys
import unittest

# A workaround trick for importing source modules. Just fine for testing.
sys.path.append(os.path.abspath("."))

# pylint: disable = wrong-import-position
from db import (
    BaseTableDatabase,
    DatabaseNative,
    MasterDatabase,
    gen_password_hash,
    check_password_hash,
)


class SampleUserDatabase(BaseTableDatabase):
    """
    The database (table) for user identity.
    """

    def __init__(self, db: DatabaseNative) -> None:
        super().__init__(
            "users",
            db,
            {
                "columns": {
                    "user_id": {
                        "dtype": "int",
                        "primary": True,
                        "auto_increment": True,
                    },
                    "permissions": {"dtype": "int"},
                    "auth_method": {"dtype": "str"},
                },
            },
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
        with open(".test/_db_basic_database.db", "w", encoding="utf-8"):
            # truncate test db file
            pass

        self.db = DatabaseNative(".test/_db_basic_database.db")
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

        os.remove(".test/_db_basic_database.db")


class TestFakeDatabaseInit(unittest.TestCase):
    """
    Tests fake_db_init
    """

    def setUp(self):
        os.makedirs(".test", exist_ok=True)
        with open(".test/_db_fake_database.db", "w", encoding="utf-8"):
            # truncate test db file
            pass

        self.db = MasterDatabase(".test/_db_fake_database.db")

        self.SYMPTOMS = [
            {"name": "發燒", "academic": "pyrexia", "visit": 3579},
            {"name": "紅疹", "academic": "rash", "visit": 1324},
            {"name": "下腹疼痛", "academic": "abdominal-pain", "visit": 1223},
            {"name": "頭暈", "academic": "vertigo", "visit": 1139},
            {"name": "畏寒", "academic": "rigor", "visit": 1024},
            {"name": "腹瀉", "academic": "diarrhea", "visit": 1591},
            {"name": "皮膚過敏", "academic": "allergic-dermatitis", "visit": 1234},
            {"name": "流鼻水", "academic": "rhinorrhea", "visit": 1842},
            {"name": "打噴嚏", "academic": "sneeze", "visit": 924},
            {"name": "偏頭痛", "academic": "migraine", "visit": 434},
            {"name": "牙齦紅腫", "academic": "gingivitis", "visit": 124},
            {"name": "口臭", "academic": "halitosis", "visit": 324},
        ]

        self.OO_MAN_NEWS = [
            {
                "class": "warning",
                "user_id": 1,
                "title": "驚爆！！！大O男出沒中央大學！",
                "content": "城市驚現超級大O男，引起市民熱議和媒體關注，成為社交媒體熱門話題。",
                "update_at": "2024/03/18 22:47:14",
                "create_at": "2024/03/18 22:47:14",
            }
        ]

        with open("data/clinics.jsonl", "r", encoding="utf8") as file:
            self.CLINICS = [json.loads(line) for line in file]

        self.db.create("symptoms", self.SYMPTOMS)
        # for s in self.SYMPTOMS:
        #     self.db.create("symptoms", s)

        self.db.create("bulletins", self.OO_MAN_NEWS)
        # for every_man in self.OO_MAN_NEWS:
        #     self.db.create("bulletins", every_man)

        self.doctor = self.db.create(
            "users",
            {
                "username": "real_doctor",
                "password": gen_password_hash("safe_password"),
                "permission": 1,
                "auth_method": "password",  # Facebook, Google, ..., etc.
            },
        )

        self.clinics = []
        for clinic in self.CLINICS:  # need a owner
            self.clinics.append(
                {
                    "title": clinic["name"],
                    "address": clinic["address"],
                    "tel": clinic["number"],
                    "owner_id": self.doctor["user_id"],
                    "tags": (
                        self.get_random_items(
                            ["家庭醫學", "婦科", "皮膚", "內分泌", "泌尿"]
                        )
                    ),
                }
            )

        self.db.create("clinics", self.clinics)

    def get_random_items(self, array, count=None):
        if count is None:
            count = random.randint(1, len(array) // 2)
        return random.sample(array, count)

    def testClinics(self):
        res = self.db.read("clinics", {"name": "萬安中醫診所"})
        assert any(ent["address"] == "台中市西屯區重慶路１３１號１樓" for ent in res)

        # PyPika does not support SQLite substr() yet
        # See: pypika.functions
        # tb = self.db.get_table("clinics")
        # table, _ = tb.criterion_selector()
        # assert len(tb.query(fn.Substring(table.address, 1, 3) == "高雄市")) == 441

        res = self.db.read("clinics", select_fields=("address",))
        assert list(map(lambda clinic: clinic["address"], self.CLINICS)) == list(
            map(lambda clinic: clinic["address"], res)
        )

    def testUsers(self):
        res = self.db.read("users")
        assert len(res) == 1 and check_password_hash(
            "safe_password", res[0]["password"]
        )

    def testSymptoms(self):
        assert (
            self.db.read("symptoms", select_fields=("name", "academic", "visit"))
            == self.SYMPTOMS
        )

    def testBulletins(self):
        res = self.db.read("bulletins")
        assert len(res) == 1 and "社交媒體熱門話題" in res[0]["content"]

    def tearDown(self):
        del self.db

        os.remove(".test/_db_fake_database.db")


if __name__ == "__main__":
    unittest.main()
