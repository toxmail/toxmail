import os
import hashlib
import functools

from bonzo.server import SMTPConnection as _SMTPConnection
from tornado.tcpserver import TCPServer
from tornado import ioloop

from pyzmail import PyzMessage

CRLF = '\r\n'


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
        hash = hashlib.md5(mail).hexdigest()
        with open(os.path.join(self.storage, hash), 'w') as f:
            f.write(mail)

    def handle_stream(self, stream, address):
        SMTPConnection(stream, address, self._callback)


class SMTPConnection(_SMTPConnection):
    def _on_data(self, data):
        try:
            self.request_callback(data)
        except Exception, e:
            print str(e)
            self.write("554 " + str(e))
        else:
            self.write("250 Ok")

    def _on_commands(self, line):
        if self.__state == self.COMMAND:
            if not line:
                self.write('500 Error: bad syntax')
                return
            i = line.find(' ')
            if i < 0:
                raw_command = line.strip()
                arg = None
            else:
                raw_command = line[:i].strip()
                arg = line[i + 1:].strip()
            method = getattr(self, 'command_' + raw_command.lower(), None)
            if not method:
                self.write('502 Error: command "%s" not implemented' %
                           raw_command)
                return
            method(arg)
        elif self.__state == self.DATA:
            data = []
            for text in line.split(CRLF):
                if text and text[0] == '.':
                    data.append(text[1:])
                else:
                    data.append(text)
            self.__data = '\n'.join(data)
            self.__rcpttos = []
            self.__mailfrom = None
            self.__state = self.COMMAND
            self._on_data(self.__data)
        else:
            self.write('451 Internal confusion')
