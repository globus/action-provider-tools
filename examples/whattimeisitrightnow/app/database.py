import dbm
import os
import pickle


class DummyDatabase:
    filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "whattimeisitrightnow.example.db"
    )

    def persist(self, key, value):
        with dbm.open(self.filename, "c") as db:
            db[key] = pickle.dumps(value)

    def query(self, key):
        with dbm.open(self.filename, "c") as db:
            val = db.get(key, pickle.dumps(None))
        return pickle.loads(val)

    def delete(self, key):
        with dbm.open(self.filename, "c") as db:
            del db[key]


db = DummyDatabase()
