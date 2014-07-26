import asyncore
import json
from os.path import exists
from time import sleep
import chardet
import sys
import argparse

import tornado

from toxmail.toxclient import ToxClient
from toxmail.dashboard import application as webapp
from toxmail.smtp import SMTPServer
from toxmail.pop3 import POP3Server

from toxmail import __version__


def main():
    parser = argparse.ArgumentParser(description='ToxMail Node.')

    parser.add_argument('--smtp-port', type=int, default=2525,
                        help="SMTP port")

    parser.add_argument('--pop3-port', type=int, default=2626,
                        help="POP3 port")

    parser.add_argument('--web-port', type=int, default=8080,
                        help="Dashboard port")

    parser.add_argument('--tox-data', type=str, default='data',
                        help="Tox data file path")

    parser.add_argument('--maildir', type=str, default=None,
                        help="Maildir to store mails")

    parser.add_argument('--version', action='store_true', default=False,
                        help='Displays version and exits.')


    args = parser.parse_args()
    if args.version:
        print(__version__)
        sys.exit(0)

    if args.maildir is None:
        args.maildir = args.tox_data + '.mails'

    print('ToxMail node starting...')
    print('Serving SMTP on localhost:%d' % args.smtp_port)
    print('Serving POP3 on localhost:%d' % args.pop3_port)
    print('Serving Dashboard on localhost:%d' % args.web_port)

    tox = ToxClient(args.tox_data)
    smtp = SMTPServer(tox.send_mail)
    smtp.listen(args.smtp_port)

    webapp.tox = tox
    webapp.listen(args.web_port)

    pop3 = POP3Server(args.maildir)
    pop3.listen(args.pop3_port)

    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        tox.save()
        pop3.close()
