# inspired from
# http://code.activestate.com/recipes/534131-toxpop-python-pop3-server/
import logging
import os
import socket
import sys
import traceback
import errno

from tornado import ioloop
from toxmail.mails import Mails

logging.basicConfig(format="%(name)s %(levelname)s - %(message)s")
log = logging.getLogger("toxmail")
log.setLevel(logging.INFO)


class Connection(object):
    END = "\r\n"
    def __init__(self, conn):
        self.conn = conn

    def __getattr__(self, name):
        return getattr(self.conn, name)

    def sendall(self, data, END=END):
        if len(data) < 50:
            log.debug("send: %r", data)
        else:
            log.debug("send: %r...", data[:50])
        data += END
        self.conn.sendall(data)

    def recvall(self, END=END):
        data = []
        while True:
            try:
                chunk = self.conn.recv(4096)
            except socket.error, e:
                if e.args[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                    raise
                continue

            if END in chunk:
                data.append(chunk[:chunk.index(END)])
                break
            data.append(chunk)
            if len(data) > 1:
                pair = data[-2] + data[-1]
                if END in pair:
                    data[-2] = pair[:pair.index(END)]
                    data.pop()
                    break
        log.debug("recv: %r", "".join(data))
        return "".join(data)


class Handler(object):

    def __init__(self, maildir='mails'):
        self.maildir = Mails(maildir)

    def USER(self, data):
        return "+OK user accepted"

    def PASS(self, data):
        return "+OK pass accepted"

    def STAT(self, data):
        num = len(self.maildir)
        total = 0

        for msg in self.maildir:
            num += 1
            total += len(str(msg))

        return "+OK %d %i" % (num, total)

    def _get_sorted(self):
        mails = [(key, msg) for key, msg in self.maildir.iteritems()]
        mails.sort()
        return mails

    def LIST(self, data):
        num = len(self.maildir)
        total = 0
        res = []
        index = 0

        for key, msg in self._get_sorted():
            total += len(msg)
            res.append("%d %d" % (index+1, len(msg)))

        res.insert(0, "+OK %d messages (%i octets)" % (num, total))
        res = "\r\n".join(res) + "\r\n."
        return res

    def TOP(self, data):
        raise NotImplementedError()

    def RETR(self, data):
        index = int(data.split()[-1]) - 1
        __, msg = self._get_sorted()[index]
        return "+OK %i octets\r\n%s\r\n." % (len(msg), msg)

    def DELE(self, data):
        index = int(data.split()[-1]) - 1
        key, __ = self._get_sorted()[index]
        self.maildir.remove(key)
        return "+OK message %d deleted" % (index + 1)

    def NOOP(self, data):
        return "+OK"

    def QUIT(self, data):
        return "+OK toxpop POP3 server signing off"


class POP3Server(object):

    def __init__(self, maildir):
        self.maildir = maildir
        self.handler = Handler(self.maildir)
        self.sock = None
        self.loop = ioloop.IOLoop.current()

    def listen(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(0)
        self.sock.bind(('localhost', port))
        self.sock.listen(128)
        self.loop = ioloop.IOLoop.current()
        self.loop.add_handler(self.sock.fileno(), self._ready, self.loop.READ)

    def close(self):
        self.loop.remove_handler(self.sock.fileno())
        self.sock.close()

    def _ready(self, fd, events):
        while True:
            try:
                conn, addr = self.sock.accept()
            except socket.error, e:
                if e.args[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                    raise
                return

            conn.setblocking(0)

            # XXX make block async
            try:
                conn = Connection(conn)
                conn.sendall("+OK toxpop file-based pop3 server ready")
                while True:
                    data = conn.recvall()
                    if data == '':
                        continue

                    print data
                    command = data.split(None, 1)[0]

                    try:
                        cmd = getattr(self.handler, command)
                    except AttributeError:
                        conn.sendall("-ERR unknown command")
                    else:
                        conn.sendall(cmd(data))
                        if command is 'QUIT':
                            break
            finally:
                conn.close()
                msg = None
