import asyncore
from smtpd import SMTPServer
import json
from os.path import exists
from time import sleep
import chardet

import tornado

from bonzo.server import SMTPServer
from toxsmtp.toxclient import ToxClient
from pyzmail import PyzMessage


class SMTP(SMTPServer):
    def _on_data(self, data):
        message = email.message_from_string(data)
        msg = PyzMessage.factory(payload)
        self.write("250 Ok")
        self.request_callback(msg)


def main():
    print('Serving on localhost:2525')
    tox = ToxClient()
    smtp = SMTP(tox.send_mail)
    smtp.listen(2525)
    tornado.ioloop.IOLoop.current().start()
