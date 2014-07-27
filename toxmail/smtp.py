import os
import hashlib
import functools

from bonzo.server import SMTPConnection as _SMTPConnection
from tornado.tcpserver import TCPServer
from tornado import ioloop

from pyzmail import PyzMessage


class SMTPServer(TCPServer):
    def __init__(self, storage, sender, io_loop=None, **kwargs):
        TCPServer.__init__(self, io_loop=io_loop, **kwargs)
        self.storage = storage
        if not os.path.exists(self.storage):
            os.mkdir(self.storage)
        self.loop = io_loop or ioloop.IOLoop.current()
        self.send_mail = sender
        self.loop.call_later(10, self.send_mails)

    def send_mails(self):
        for mail in os.listdir(self.storage):
            if mail.endswith('.sending'):
                continue
            path = os.path.join(self.storage, mail)
            sending_path = path + '.sending'
            os.rename(path, sending_path)

            with open(sending_path) as f:
                print 'sending %s' % path
                mail = PyzMessage.factory(f.read())
                callback = functools.partial(self._send_callback, path)
                try:
                    self.send_mail(mail, callback)
                except Exception, e:
                    print str(e)

        self.loop.call_later(10, self.send_mails)

    def _send_callback(self, mail, result):
        if result:
            print 'Success'
            os.remove(mail + '.sending')
        else:
            print 'Failure, added back'
            os.rename(mail + '.sending', mail)

    def _callback(self, mail):
        mail = str(mail)
        hash = hashlib.md5(mail).hexdigest()
        with open(os.path.join(self.storage, hash), 'w') as f:
            f.write(mail)

    def handle_stream(self, stream, address):
        SMTPConnection(stream, address, self._callback)


class SMTPConnection(_SMTPConnection):
    def _on_data(self, data):
        data = str(data)
        msg = PyzMessage.factory(data)
        try:
            self.request_callback(msg)
        except Exception, e:
            print str(e)
            self.write("554 " + str(e))
        else:
            self.write("250 Ok")
