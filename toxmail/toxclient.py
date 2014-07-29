from tox import Tox, OperationFailedError
import tornado
import os.path
import hashlib
from toxmail.mails import Mails


_SERVER = ["54.199.139.199", 33445,
           "7F9C31FE850E97CEFD4C4591DF93FC757C7C12549DDD55F8EEAECC34FE76C029"]


class ToxClient(Tox):

    def __init__(self, data='data', maildir=None, contacts=None,
                 io_loop=None, server=None):
        self.contacts = contacts
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
        self._files = {}

    def save(self):
        self.save_to_file(self.data)

    def on_file_send_request(self, friend_id, file_id, size, filename):
        print 'File request accepted.'
        self._files[file_id] = size, filename, ''
        self.file_send_control(friend_id, 1, file_id, Tox.FILECONTROL_ACCEPT)
        self.do()

    def on_file_control(self, friend_id, receive_send, file_id, ct, data):
        if receive_send == 1 and ct == Tox.FILECONTROL_ACCEPT:
            print 'Friend accepting the file'
        elif receive_send == 0 and ct == Tox.FILECONTROL_FINISHED:
            # all data sent over
            print 'all data sent'
            size, filename, received = self._files[file_id]
            self._mail_received(friend_id, received)
            del self._files[file_id]
        else:
            print 'file control'
            print 'receive_send ' + str(receive_send)
            print 'file_id ' + str(file_id)
            print 'ct ' + str(ct)
        self.do()

    def on_file_data(self, friend_id, file_id, data):
        print 'receiving data'
        size, filename, received = self._files[file_id]
        received += data
        self._files[file_id] = size, filename, received

    def on_friend_request(self, address, message):
        print('Not taking friend requests here.')

    def on_friend_message(self, friend_id, message):
        print('using files to send messages.')

    def _mail_received(self, friend_id, mail):
        print 'Mail Received.'
        self.mails.add(mail)

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

        if not self.get_friend_connection_status(friend_id):
            print('Friend not connected')
            cb(False)
            return

        mail['X-Tox-Client-Id'] = client_id
        mail = str(mail)
        self._send_mail(client_id, friend_id, mail, cb)

    def _to_friend_id(self, client_id):
        return self.get_friend_id(client_id)

    def _later(self, *args, **kw):
        return self.io_loop.call_later(self.interval, *args, **kw)

    def _send_mail(self, client_id, friend_id, mail, cb, tries=0):
        self.do()
        mail = str(mail)
        hash = hashlib.md5(mail).hexdigest()
        chunk_size = self.file_data_size(friend_id)
        try:
            file_id = self.new_file_sender(friend_id, len(mail), hash)
        except OperationFailedError:
            if tries > 10:
                cb(False)
                return

            self.io_loop.call_later(self.interval*10,
                                    self._send_mail, client_id,
                                    friend_id, mail, cb, tries+1)
            return

        print 'now sending chunks'
        start = 0
        end = start + chunk_size
        self.do()
        self.io_loop.add_callback(self._send_chunk, file_id, friend_id,
                                  mail, start, end, cb)

    def _send_chunk(self, file_id, friend_id, mail, start, end, cb, tries=0):

        total_size = len(mail)

        chunk_size = self.file_data_size(friend_id)
        if end > total_size:
            end = total_size

        print 'sending chunk %d=>%d out of %d' % (start, end, len(mail))
        data = mail[start:end]
        self.do()

        try:
            self.file_send_data(friend_id, file_id, data)
        except OperationFailedError:
            if tries > 200:
                cb(False)
                return
            self.io_loop.call_later(self.interval*10, self._send_chunk,
                                    file_id, friend_id, mail, start,
                                    end, cb, tries+1)
            return

        print 'chunk sent'
        if total_size > end:
            # need more sending
            start = end

            if len(mail) > start + chunk_size:
                end = start + chunk_size
            else:
                end = total_size

            self.io_loop.add_callback(self._send_chunk, file_id,
                                      friend_id, mail, start,
                                      end, cb)
        else:
            # done
            self.file_send_control(friend_id, 0, file_id,
                                   Tox.FILECONTROL_FINISHED)
            self.do()
            cb(True)

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
