import asyncore
import json
from os.path import exists
from time import sleep
import chardet
import sys

import tornado

from bonzo.server import SMTPServer
from toxsmtp.toxclient import ToxClient
from pyzmail import PyzMessage


class SMTP(SMTPServer):
    def _on_data(self, data):
        message = email.message_from_string(data)
        msg = PyzMessage.factory(payload)
        try:
            self.request_callback(msg)
        except Exception, e:
            print str(e)
            self.write("554 " + str(e))
        else:
            self.write("250 Ok")


def main():
    if len(sys.argv) > 1:
        data = sys.argv[1]
    else:
        data = 'data'
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    else:
        port = 2525


    print('Serving on localhost:%d' % port)
    tox = ToxClient(data)
    smtp = SMTP(tox.send_mail)
    smtp.listen(port)
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        tox.save()
