import sys
import argparse
import tornado

from toxmail.toxclient import ToxClient
from toxmail.dashboard import application as webapp
from toxmail.smtp import SMTPServer
from toxmail.pop3 import POP3Server
from toxmail.contacts import Contacts

from toxmail import __version__


def main():
    parser = argparse.ArgumentParser(description='ToxMail Node.')

    parser.add_argument('--smtp-port', type=int, default=2525,
                        help="SMTP port")

    parser.add_argument('--pop3-port', type=int, default=2626,
                        help="POP3 port")

    parser.add_argument('--web-port', type=int, default=8080,
                        help="Dashboard port")

    parser.add_argument('--tox-data', default='data',
                        help="Tox data file path")

    parser.add_argument('--smtp-storage', type=str, default='',
                        help="Storage for outgoing e-mail")

    parser.add_argument('--contacts-db', type=str, default='',
                        help="Storage for contacts")

    parser.add_argument('--maildir', type=str, default='',
                        help="Maildir to store mails")

    parser.add_argument('--version', action='store_true', default=False,
                        help='Displays version and exits.')

    args = parser.parse_args()
    if args.version:
        print(__version__)
        sys.exit(0)

    if not args.maildir:
        args.maildir = args.tox_data + '.mails'

    if not args.smtp_storage:
        args.smtp_storage = args.tox_data + '.out'

    if not args.contacts_db:
        args.contacts_db = args.tox_data + '.contacts'

    print('ToxMail node starting...')
    print('Contact Database %r' % args.contacts_db)
    print('Maildir %r' % args.maildir)
    print('SMTP Storage %r' % args.smtp_storage)
    print('Serving SMTP on localhost:%d' % args.smtp_port)
    print('Serving POP3 on localhost:%d' % args.pop3_port)
    print('Serving Dashboard on localhost:%d' % args.web_port)

    contacts = Contacts(args.contacts_db)
    tox = ToxClient(args.tox_data, contacts=contacts)
    smtp = SMTPServer(args.smtp_storage, tox.send_mail)
    smtp.listen(args.smtp_port)

    webapp.tox = tox
    webapp.config = args
    webapp.contacts = contacts
    webapp.listen(args.web_port)

    pop3 = POP3Server(args.maildir)
    pop3.listen(args.pop3_port)

    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        tox.save()
        contacts.save()
        pop3.close()
