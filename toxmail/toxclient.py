import json
import hashlib
import os.path

from tox import Tox
import tornado
from nacl.public import PublicKey, PrivateKey

from toxmail.mails import Mails
from toxmail.util import FileHandler
from toxmail.crypto import encrypt_text


_SERVER = ["54.199.139.199", 33445,
           "7F9C31FE850E97CEFD4C4591DF93FC757C7C12549DDD55F8EEAECC34FE76C029"]
_SUPERNODE = ('7683702CDED6EA0CD7A87D506A70A10CD14'
              '5195D7ED4B6687641CDAC437C9B30CD254928B4F9')


class ToxClient(Tox):

    def __init__(self, data='data', maildir=None, relaydir=None,
                 contacts=None,
                 io_loop=None, server=None, supernode=_SUPERNODE):
        self.contacts = contacts
        if server is None:
            server = _SERVER
        self.data = data
        if os.path.exists(data):
            self.load_from_file(data)

        self.privkey, self.pubkey = self.get_keys()
        self.pubkey = PublicKey(self.pubkey.decode('hex'))
        self.privkey = PrivateKey(self.privkey.decode('hex'))
        self.supernode_pbkey = PublicKey(supernode[:64].decode('hex'))

        self.server = server
        self.io_loop = io_loop or tornado.ioloop.IOLoop.current()
        self.bootstrap_from_address(self.server[0], 1,
                                    self.server[1],
                                    self.server[2])
        self.io_loop.add_callback(self._init)
        self.interval = self.do_interval() / 1000.
        if maildir is None:
            maildir = data + '.mails'
        self.mails = Mails(maildir)
        self.relaydir = relaydir
        self.supernode = supernode
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
        content = mail_data['mail']

        if target == self.get_address():
            self.mails.add(content)
        else:
            # relaying
            print 'Mail to be relayed.'
            hash = hashlib.md5(mail).hexdigest()
            with open(os.path.join(self.relaydir, hash), 'w') as f:
                f.write(mail)

    def relay_mail(self, mail_data, cb):
        raise NotImplementedError()

    def send_mail(self, mail, cb):
        to = mail['To']
        client_id = None
        contact = self.contacts.get(to)
        if contact is not None:
            client_id = contact.get('client_id')

        if client_id is None and to.endswith('@tox'):
            client_id = to[:-len('@tox')].strip()

        if client_id is None:
            print('Could not send to %s' % mail)
            raise ValueError('Unknown contact.')

        friend_id = self._to_friend_id(client_id)
        if friend_id is None:
            print('Could not send to %s' % client_id)
            raise ValueError('Unknown Tox friend.')

        # XXX later: instead of sending it to a supernode,
        # send it to all online friends - they can be used as relays.
        # once the message finally makes it, it can be deleted everywhere.
        #
        to_supernode = False
        if not self.get_friend_connection_status(friend_id):
            print('Friend not connected')
            # check if the supernode is connected
            supernode_fid = self._to_friend_id(self.supernode)
            if supernode_fid is None:
                print('Could not send to %s' % supernode_fid)
                raise ValueError('Unknown Tox friend.')

            if self.get_friend_connection_status(supernode_fid):
                # it's connected, we send the mail to the supernode.
                to_supernode = True
            else:
                print('Supernode not connected')
                cb(False)
                return

        mail['X-Tox-Client-Id'] = client_id
        mail = str(mail)
        hash = hashlib.md5(mail).hexdigest()

        if to_supernode:
            # sending to supernode
            mail = encrypt_text(mail, self.privkey, self.supernode_pbkey)
            data = {'mail': mail.encode('hex'), 'client_id': client_id,
                    'hash': hash}
            data = json.dumps(data)
            self.file_handler.send_file(self.supernode, supernode_fid,
                                        data, cb)
        else:
            # sending directly to rcpt
            data = {'mail': mail.encode('hex'), 'client_id': client_id,
                    'hash': hash}
            data = json.dumps(data)
            self.file_handler.send_file(client_id, friend_id, data, cb)

    def _to_friend_id(self, client_id):
        return self.get_friend_id(client_id)

    def _later(self, *args, **kw):
        return self.io_loop.call_later(self.interval, *args, **kw)

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
