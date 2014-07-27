import mailbox


class Mails(mailbox.Maildir):
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
