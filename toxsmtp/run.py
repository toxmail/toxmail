import asyncore
from smtpd import SMTPServer


class Server(SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data):
        raise NotImplementedError()


def main():
    print('Serving on localhost:26')
    server = Server(('localhost', 26), None)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        print('Bye')
