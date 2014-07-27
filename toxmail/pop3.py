import socket
import errno
from tornado import ioloop, iostream
from toxmail.mails import Mails


class Connection(object):
    def __init__(self, connection, handler):
        self.stream = iostream.IOStream(connection)
        self.handler = handler
        self.write("+OK toxmail file-based pop3 server ready")
        self._read()

    def write(self, data):
        self.stream.write(data + '\r\n')

    def _read(self):
        self.stream.read_until('\r\n', self._eol_callback)

    def _eol_callback(self, data):
        self.handle_data(data)

    def handle_data(self, data):
        command = data.split(None, 1)[0]
        print command
        try:
            cmd = getattr(self.handler, command)
        except AttributeError:
            self.write("-ERR unknown command")
        else:
            self.write(cmd(data))
            if command is 'QUIT':
                self.stream.close()
                self.connection.close()

        self._read()


class Handler(object):

    def __init__(self, maildir='mails'):
        self.maildir = Mails(maildir)

    def CAPA(self, data):
        answer = ['+OK', 'TOP', 'USER', '.']
        return '\r\n'.join(answer)

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
            print key
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
        # XXX should stream here
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
            else:
                conn.setblocking(0)
                Connection(conn, self.handler)
