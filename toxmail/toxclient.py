import json
import hashlib
import os.path

from tox import Tox
import tornado

from toxmail.mails import Mails
from toxmail.util import FileHandler
from toxmail.crypto import encrypt_text, decrypt_text


_SERVER = ["54.199.139.199", 33445,
           "7F9C31FE850E97CEFD4C4591DF93FC757C7C12549DDD55F8EEAECC34FE76C029"]


class ToxClient(Tox):

    def __init__(self, data='data', maildir=None, relaydir=None,
                 contacts=None, io_loop=None, server=None,
                 config=None):
        self.contacts = contacts
        self.config = config
        if server is None:
            server = _SERVER
        self.data = data
        if os.path.exists(data):
            self.load_from_file(data)

        self.pubkey, self.privkey = self.get_keys()
        self.server = server
        self.io_loop = io_loop or tornado.ioloop.IOLoop.current()
        self.bootstrap_from_address(self.server[0],
                                    self.server[1],
                                    self.server[2])
        self.io_loop.add_callback(self._init)
        self.interval = self.do_interval() / 1000.
        if maildir is None:
            maildir = data + '.mails'
        self.mails = Mails(maildir)
        self.relaydir = relaydir
        self.file_handler = FileHandler(self, self._mail_received,
                                        self.io_loop)

    def save(self):
        self.save_to_file(self.data)

    def on_friend_request(self, address, message):
        print('Not taking friend requests here.')

    def on_friend_message(self, friend_id, message):
        print('using files to send messages.')

    def _mail_received(self, friend_id, mail):
        print 'Mail Received.'
        mail_data = json.loads(mail)
        # is this a mail for myself or are we relaying ?
        target = mail_data['client_id']
        content = mail_data['mail'].decode('hex')

        if target == self.get_address():
            senderkey = mail_data['sender'][:64]

            encrypted = mail_data.get('encrypted', False)
            if encrypted:
                content = decrypt_text(content, self.privkey, senderkey)

            self.mails.add(content)
        else:
            # relaying
            print 'Mail to be relayed.'
            hash = hashlib.md5(mail).hexdigest()
            with open(os.path.join(self.relaydir, hash), 'w') as f:
                f.write(mail)

    def relay_mail(self, mail_data, cb):
        client_id = mail_data['client_id']
        friend_id = self._to_friend_id(client_id)
        if friend_id is None:
            raise ValueError('Unknown Tox friend.')

        if self.get_friend_connection_status(friend_id):
            print('Friend %s is not online.' % client_id)
            cb(False)
            return

        data = json.dumps(mail_data)
        self.file_handler.send_file(client_id, friend_id, data, cb)

    def get_online_friends(self):
        # XXX filter out friends that are not checked as relays
        online = []
        for fid in self.get_friendlist():
            self.do()
            if self.get_friend_connection_status(fid):
                online.append((fid, self.get_client_id(fid)))
        return online

    def send_mail(self, mail, cb):
        to = mail['To']
        client_id = None
        contact = self.contacts.get(to)
        if contact is not None:
            client_id = contact.get('client_id')

        if client_id is None and to.endswith('@tox'):
            client_id = to[:-len('@tox')].strip()

        if client_id is None:
            raise ValueError('Unknown contact.')

        friend_id = self._to_friend_id(client_id)
        if friend_id is None:
            raise ValueError('Unknown Tox friend.')

        to_relay = False
        relay_friend_id = relay_id = None

        if not self.get_friend_connection_status(friend_id):
            print('Friend not connected')

            # check if the relay mode is activated
            if self.config.get('activate_relay', False):
                relay_id = self.config['relay_id']
                relay_friend_id = self._to_friend_id(relay_id)

                if relay_friend_id is None:
                    raise ValueError('Unknown Tox node.')

                if not self.get_friend_connection_status(relay_friend_id):
                    print('Relay node not online.')
                    cb(False)
                    return

                to_relay = True

        mail['X-Tox-Client-Id'] = client_id
        mail = str(mail)
        hash = hashlib.md5(mail).hexdigest()

        if to_relay:
            # sending to the relay
            client_key = client_id[:64]
            mail = encrypt_text(mail, self.privkey, client_key)
            data = {'mail': mail.encode('hex'), 'client_id': client_id,
                    'hash': hash, 'encrypted': True,
                    'sender': self.get_address()}
            data = json.dumps(data)

            self.file_handler.send_file(relay_id, relay_friend_id, data, cb)
        else:
            # sending directly to rcpt
            data = {'mail': mail.encode('hex'), 'client_id': client_id,
                    'hash': hash, 'encrypted': False,
                    'sender': self.get_address()}
            data = json.dumps(data)
            self.file_handler.send_file(client_id, friend_id, data, cb)

    def _to_friend_id(self, client_id):
        return self.get_friend_id(client_id)

    def _later(self, *args, **kw):
        return self.io_loop.call_later(self.interval, *args, **kw)

    def on_connected(self):
        print('Connected to Tox.')
        print('ID: %s' % self.get_address())
        self.set_user_status(Tox.USERSTATUS_NONE)

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
        if not self.isconnected():
            print('Disconnected from DHT - reconnecting')
            self.bootstrap_from_address(self.server[0], 1,
                                        self.server[1],
                                        self.server[2])

        self.do()
        self._later(self._do)
