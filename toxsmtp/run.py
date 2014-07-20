import asyncore
from smtpd import SMTPServer
import json
from os.path import exists
from time import sleep
import maillib
import chardet

from tox import Tox

SERVER = ["54.199.139.199", 33445,
"7F9C31FE850E97CEFD4C4591DF93FC757C7C12549DDD55F8EEAECC34FE76C029"]
DATA = 'data'
_ID = ('360E674BA34A8C761E9AE8858CCBFC8789A2A0FF9'
       'D42D2AF12340318D04A0E73FCC1E7314A7F')


class ToxSender(Tox):
    def __init__(self):
        if exists(DATA):
            self.load_from_file(DATA)

    def loop(self, n=10):
        interval = self.do_interval()
        for i in range(n):
            self.do()
            sleep(interval / 1000.0)

    def __call__(self, peer, message):
        self.set_name("ToxSMTP")
        print('ID: %s' % self.get_address())
        self.bootstrap_from_address(SERVER[0], 1, SERVER[1], SERVER[2])

        # loop until connected
        while not self.isconnected():
            self.loop(50)

        print('Connected')
        # loop until sent
        # TODO = convert peer e-mail to friend_id
        friend_id = 0
        THRESHOLD = 200
        sent = False
        count = 0

        while not sent:
            try:
                self.send_message(friend_id, message)
                sent = True
            except Exception, e:
                if count > THRESHOLD:
                    raise
                self.loop(50)
                count += 1
                print str(e)


def send_mail(peer, mailfrom, rcpttos, data):
    data = data.decode(chardet.detect(data)['encoding'])
    mail = {'mailfrom': mailfrom, 'rcpttos': rcpttos, 'data': data}
    mail = json.dumps(mail)
    if len(mail) > 1368:
        raise NotImplementedError()

    sender = ToxSender()
    sender(peer, mail)


class Server(SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data):
        send_mail(peer, mailfrom, rcpttos, data)


def main():
    print('Serving on localhost:2525')
    server = Server(('localhost', 2525), None)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        print('Bye')
