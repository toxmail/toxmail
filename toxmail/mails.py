import mailbox
import email.utils
import os


class Mails(mailbox.Maildir):
    def add(self, raw):
        mail = mailbox.mboxMessage(raw)
        self.lock()
        try:
            super(Mails, self).add(mail)
            self.flush()
        finally:
            self.unlock()

    def remove(self, key):
        self.lock()
        try:
            super(Mails, self).remove(key)
            self.flush()
        finally:
            self.unlock()
