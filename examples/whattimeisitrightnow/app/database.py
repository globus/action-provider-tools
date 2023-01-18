import pickle


class DummyDatabase:
    def __init__(self):
        self.db = {}

    def persist(self, key, value):
        self.db[key] = pickle.dumps(value)

    def query(self, key):
        val = self.db.get(key, pickle.dumps(None))
        return pickle.loads(val)

    def delete(self, key):
        del self.db[key]


db = DummyDatabase()
