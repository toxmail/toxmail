import mailbox


class Mails(mailbox.Maildir):
    def __init__(self, path):
        mailbox.Maildir.__init__(self, path, self._factory, create=True)

    def _factory(self, file):
        return file.read()

    def add(self, raw):
        mail = mailbox.mboxMessage(raw)
        self.lock()
        try:
            mailbox.Maildir.add(self, mail)
            self.flush()
        finally:
            self.unlock()

    def remove(self, key):
        self.lock()
        try:
            mailbox.Maildir.remove(self, key)
            self.flush()
        finally:
            self.unlock()
