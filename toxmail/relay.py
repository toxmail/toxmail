import os
import json
import functools

from tornado import ioloop


class Relay(object):
    def __init__(self, relaydir, relayer, io_loop=None):
        self.storage = relaydir
        if not os.path.exists(relaydir):
            os.mkdir(relaydir)
        self.loop = io_loop or ioloop.IOLoop.current()
        self.loop.call_later(5, self.relay_mails)
        self.relayer = relayer
        self.running = False

    def relay_mails(self):
        if not self.running:
            return
        for mail in os.listdir(self.storage):
            if mail.endswith('.sending'):
                continue

            path = os.path.join(self.storage, mail)
            sending_path = path + '.sending'
            os.rename(path, sending_path)

            with open(sending_path) as f:
                print 'relaying %s' % path
                mail_data = json.loads(f.read())
                callback = functools.partial(self._relay_callback, path)
                try:
                    self.relayer(mail_data, callback)
                except Exception, e:
                    print str(e)

        self.loop.call_later(5, self.relay_mails)

    def _relay_callback(self, path, result):
        if result:
            print 'Success'
            os.remove(path + '.sending')
        else:
            print 'Failure, added back'
            os.rename(path + '.sending', path)

    def stop(self):
        self.running = False
