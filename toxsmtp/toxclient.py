from tox import Tox
import tornado
import os.path
from pyzmail import PyzMessage
from toxsmtp.mails import Mails


DATA = 'data'
_SERVER = ["54.199.139.199", 33445,
           "7F9C31FE850E97CEFD4C4591DF93FC757C7C12549DDD55F8EEAECC34FE76C029"]


class ToxClient(Tox):

    def __init__(self, io_loop=None, server=None):
        if server is None:
            server = _SERVER
        if os.path.exists(DATA):
            self.load_from_file(DATA)
        self.server = server
        self.io_loop = io_loop or tornado.ioloop.IOLoop.current()
        self.bootstrap_from_address(self.server[0], 1,
                                    self.server[1],
                                    self.server[2])
        self.io_loop.add_callback(self._init)
        self.interval = self.do_interval() / 1000.
        self.mails = Mails()

    def on_friend_request(self, address, message):
        print('Friend added: %s' % address)
        self.add_friend_norequest(address)
        self.save_to_file(DATA)

    def on_friend_message(self, friend_id, message):
        mail = PyzMessage.factory(message)
        mail['X-Tox-Friend-Id'] = str(friend_id)
        self.mails.add(str(mail))
        print 'Mail from %s stored' % mail['X-Tox-Id']

    def _get_tox_id(self, mail):
        # TODO : find the tox id
        return 'xxx'

    #
    # TODO: store the mail in a directory and have a dedicate process
    # to send it off to ToxMail
    #
    def send_mail(self, mail):
        tox_id = ('360E674BA34A8C761E9AE8858CCBFC8789A2A0FF9D'
                  '42D2AF12340318D04A0E73FCC1E7314A7F')

        #tox_id = self._get_tox_id(mail['From'])
        mail['X-Tox-Id'] = tox_id
        mail = str(mail)

        if len(mail) > 1368:
            raise NotImplementedError()

        #friend_id = self.get_friend_id(tox_id)
        friend_id = 0
        self._send_mail(tox_id, friend_id, mail)

    def _later(self, *args, **kw):
        return self.io_loop.call_later(self.interval, *args, **kw)

    def _send_mail(self, tox_id, friend_id, mail, tries=0):
        try:
            self.send_message(friend_id, mail)
            print('Mail sent to %s.' % tox_id)
        except Exception:
            if tries > 200:
                raise
            print('Try again %d' % tries)
            self.io_loop.call_later(self.interval*10, self._send_mail,
                                    tox_id, friend_id, mail, tries+1)

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
