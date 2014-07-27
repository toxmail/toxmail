from tox import Tox
import tornado
import os.path
from pyzmail import PyzMessage

from toxmail.mails import Mails


_SERVER = ["54.199.139.199", 33445,
           "7F9C31FE850E97CEFD4C4591DF93FC757C7C12549DDD55F8EEAECC34FE76C029"]


class ToxClient(Tox):

    def __init__(self, data='data', maildir=None, io_loop=None, server=None):
        if server is None:
            server = _SERVER
        self.data = data
        if os.path.exists(data):
            self.load_from_file(data)
        self.server = server
        self.io_loop = io_loop or tornado.ioloop.IOLoop.current()
        self.bootstrap_from_address(self.server[0], 1,
                                    self.server[1],
                                    self.server[2])
        self.io_loop.add_callback(self._init)
        self.interval = self.do_interval() / 1000.
        if maildir is None:
            maildir = data+'.mails'
        self.mails = Mails(maildir)

    def save(self):
        self.save_to_file(self.data)

    def on_friend_request(self, address, message):
        # XXX this should be handled by the dashboard
        # XXX I don't know if we can have two process running
        # under the same Tox-ID or not
        #print('Friend added: %s' % address)
        #self.add_friend_norequest(address)
        #self.save_to_file(self.data)
        pass

    def on_friend_message(self, friend_id, message):
        print 'Receiving mail.'
        mail = PyzMessage.factory(message)
        mail['X-Tox-Friend-Id'] = str(friend_id)
        self.mails.add(str(mail))
        print 'Mail from %s stored' % mail['X-Tox-Id']

    def _get_tox_id(self, mail):
        # TODO : find the tox id
        return 'xxx'

    def send_mail(self, mail, cb):
        to = mail['To']
        if to.endswith('@tox'):
            tox_id = to[:-len('@tox')].strip()
        else:
            tox_id = self._get_tox_id(to)

        mail['X-Tox-Id'] = tox_id
        mail = str(mail)

        if len(mail) > 1368:
            raise NotImplementedError()

        friend_id = self._to_friend_id(tox_id)
        if friend_id is None:
            print('Could not send to %s' % tox_id)
            raise ValueError('Unknown friend')

        self._send_mail(tox_id, friend_id, mail, cb)

    def _to_friend_id(self, tox_id):
        return self.get_friend_id(tox_id)

    def _later(self, *args, **kw):
        return self.io_loop.call_later(self.interval, *args, **kw)

    def _send_mail(self, tox_id, friend_id, mail, cb, tries=0):
        try:
            self.send_message(friend_id, mail)
            print('Mail sent to %s.' % tox_id)
            cb(True)
        except Exception:
            if tries > 10:
                cb(False)
                return

            print('Try again %d' % tries)
            self.io_loop.call_later(self.interval*10, self._send_mail,
                                    tox_id, friend_id, mail, cb, tries+1)

    def on_connected(self):
        print('Connected to Tox.')
        print('ID: %s' % self.get_address())

    def _init(self):
        # keep on calling until it's connected
        if not self.isconnected():
            self.do()
            self._later(self._init)
        else:
            # we're good, calling do() periodically now
            self.on_connected()
            self._later(self._do)

    def _do(self):
        self.do()
        self._later(self._do)
