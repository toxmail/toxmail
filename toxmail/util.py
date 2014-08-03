import hashlib
import re

from tox import OperationFailedError, Tox
import tornado
import dns.resolver


class FileHandler(object):
    def __init__(self, tox, on_file_received, io_loop=None):
        self._files = {}
        self.tox = tox
        self.tox.on_file_send_request = self._on_file_send_request
        self.tox.on_file_control = self._on_file_control
        self.tox.on_file_data = self._on_file_data
        self.io_loop = io_loop or tornado.ioloop.IOLoop.current()
        self.on_file_received = on_file_received

    def _on_file_send_request(self, friend_id, file_id, size, filename):
        self._files[file_id] = size, filename, ''
        self.tox.file_send_control(friend_id, 1, file_id,
                                   Tox.FILECONTROL_ACCEPT)
        self.tox.do()

    def _on_file_control(self, friend_id, receive_send, file_id, ct, data):
        if receive_send == 1 and ct == Tox.FILECONTROL_ACCEPT:
            print('Friend accepting the file.')
        elif receive_send == 0 and ct == Tox.FILECONTROL_FINISHED:
            # all data sent over
            size, filename, received = self._files[file_id]
            self.on_file_received(friend_id, received)
            del self._files[file_id]
        self.tox.do()

    def _on_file_data(self, friend_id, file_id, data):
        size, filename, received = self._files[file_id]
        received += data
        self._files[file_id] = size, filename, received

    def send_file(self, client_id, friend_id, data, cb, tries=0):
        self.tox.do()
        hash = hashlib.md5(data).hexdigest()
        chunk_size = self.tox.file_data_size(friend_id)
        try:
            file_id = self.tox.new_file_sender(friend_id, len(data), hash)
        except OperationFailedError, e:
            if tries > 20:
                print('Could not get a file sender id')
                cb(False)
                return
            else:
                self.tox.do()

            self.io_loop.call_later(self.tox.interval*10,
                                    self.send_file, client_id,
                                    friend_id, data, cb, tries+1)
            return

        start = 0
        end = start + chunk_size
        self.tox.do()
        self.io_loop.add_callback(self._send_chunk, file_id, friend_id,
                                  data, start, end, cb)

    def _send_chunk(self, file_id, friend_id, data, start, end, cb, tries=0):
        total_size = len(data)
        print('%d=>%d (%d)' % (start, end, total_size))
        chunk_size = self.tox.file_data_size(friend_id)
        if end > total_size:
            end = total_size

        data_to_send = data[start:end]
        self.tox.do()

        try:
            self.tox.file_send_data(friend_id, file_id, data_to_send)
        except OperationFailedError:
            if tries > 200:
                print('Could not send a chunk')
                cb(False)
                return
            self.io_loop.call_later(self.tox.interval*10, self._send_chunk,
                                    file_id, friend_id, data, start,
                                    end, cb, tries+1)
            return

        if total_size > end:
            # need more sending
            start = end

            if len(data) > start + chunk_size:
                end = start + chunk_size
            else:
                end = total_size

            self.io_loop.add_callback(self._send_chunk, file_id,
                                      friend_id, data, start,
                                      end, cb)
        else:
            # done
            self.tox.file_send_control(friend_id, 0, file_id,
                                       Tox.FILECONTROL_FINISHED)
            self.tox.do()
            cb(True)


_DNS = re.compile('"v=tox1;id=([A-Z0-9]*)"')
_EMAIL = re.compile('(.*?)@(.*)')
_TOX = re.compile('[A-Z0-9]{72}')


def user_lookup(email):
    match = _EMAIL.findall(email)
    if match:
        user, domain = match[0]
        query = '%s.%s.' % (user, domain)
        try:
            answers = dns.resolver.query(query, 'TXT')
        except Exception:
            query = '%s._tox.%s.' % (user, domain)
            answers = dns.resolver.query(query, 'TXT')

        if len(answers) == 0:
            raise ValueError('No DNS entry')

        answer = str(answers[0])
        for entry in answer.strip('"').split(';'):
            entry = entry.strip()
            entry = entry.split('=')
            if len(entry) != 2:
                continue
            key, value = entry
            if key == 'id':
                return value.strip()

        raise ValueError('Wrong DNS entry - %s' % answer)
    else:
        # make sure we have a valid tox id
        if _TOX.match(email):
            return email

    raise ValueError('Invalid email or Tox-Id')
