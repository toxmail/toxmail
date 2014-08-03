# dead simple flat file database
# to lookup client_id given an e-mail
import shelve


class Contacts(object):
    def __init__(self, path):
        self.path = path
        self._db = shelve.open(path, writeback=True)

    def add(self, email, **data):
        self._db[email] = data

    def delete_first(self, **filter):
        entry = self.first(**filter)
        if entry:
            self.remove(entry['email'])

    def first(self, **filter):
        for email, entry in self._db.items():
            entry['email'] = email
            match = True
            for key, value in filter.items():
                entry_value = entry.get(key)

                if key == 'client_id':
                    value = value[:64]
                    entry_value = entry_value[:64]

                if entry_value != value:
                    match = False
                    break
            if match:
                return entry
        return None

    def get(self, email):
        return self._db.get(email)

    def remove(self, email):
        if 'email' in self._db:
            del self._db[email]

    def save(self):
        self._db.sync()
        self._db.close()
        self._db = shelve.open(self.path, writeback=True)
