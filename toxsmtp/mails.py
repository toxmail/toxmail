import mailbox
import email.utils
import os


class Mails(object):
    def __init__(self, dir='mails'):
        self.dir = dir
        self.mbox = mailbox.Maildir(self.dir)

    def add(self, raw):
        mail = mailbox.mboxMessage(raw)
        self.mbox.lock()
        try:
            self.mbox.add(mail)
            self.mbox.flush()
        finally:
            self.mbox.unlock()
