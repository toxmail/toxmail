import hashlib
from tox import OperationFailedError, Tox
import tornado


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
            print 'Friend accepting the file'
        elif receive_send == 0 and ct == Tox.FILECONTROL_FINISHED:
            # all data sent over
            print 'all data sent'
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
        except OperationFailedError:
            if tries > 10:
                cb(False)
                return

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
        chunk_size = self.tox.file_data_size(friend_id)
        if end > total_size:
            end = total_size

        data_to_send = data[start:end]
        self.tox.do()

        try:
            self.tox.file_send_data(friend_id, file_id, data_to_send)
        except OperationFailedError:
            if tries > 200:
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
