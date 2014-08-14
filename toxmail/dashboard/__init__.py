import os
from collections import defaultdict

import tornado.web
from tornado import template
from tox import OperationFailedError

from toxmail.util import user_lookup


loader = template.Loader(os.path.dirname(__file__))
# XXX add proper session handling
_SESSIONS = defaultdict(dict)


class DashboardHandler(tornado.web.RequestHandler):
    def get(self):
        session = _SESSIONS[self.request.remote_ip]
        tox = self.application.tox
        args = self.application.args
        config = self.application.config
        contacts = self.application.contacts
        my_client_id = tox.get_address()
        friends = []

        for friend_id in tox.get_friendlist():
            friend = {'friend_id': friend_id}
            client_id = tox.get_client_id(friend_id)
            friend['client_id'] = client_id
            status = tox.get_friend_connection_status(friend_id)
            friend['status'] = status and 'online' or 'offline'
            contact = contacts.first(client_id=client_id)
            if contact is not None:
                friend['email'] = contact.get('email', '')
                if friend['email'] >= 64:
                    friend['ux_email'] = (friend['email'][:4] + '...' +
                                          friend['email'][-4:])
                else:
                    friend['ux_email'] = friend['email']
                friend['relay'] = contact.get('relay', False)
            else:
                friend['email'] = ''
                friend['relay'] = False
                friend['ux_email'] = 'N/A'

            friends.append(friend)

        resp = loader.load("index.html").generate(client_id=my_client_id,
                                                  friends=friends,
                                                  args=args,
                                                  config=config,
                                                  alert=session.get('alert'))
        self.write(resp)


class RelayHandler(tornado.web.RequestHandler):
    def post(self):
        args = self.request.body_arguments
        config = self.application.config
        # XXX todo : verify data
        if 'activate_relay' in args:
            config['activate_relay'] = args['activate_relay'][0] == 'on'
        else:
            config['activate_relay'] = False

        relay_id = args['relay_id'][0]


        if relay_id:
            try:
                tox.add_friend_norequest(relay_id)
            except OperationFailedError, e:
                # XXX we want an error message
                print str(e)
                session['alert'] = str(e)
                self.redirect('/')
                return
            else:
                tox.save()

            config['relay_id'] = relay_id

        config.save()
        self.redirect('/')


class FriendHandler(tornado.web.RequestHandler):
    def post(self):
        session = _SESSIONS[self.request.remote_ip]
        client_id = self.request.body_arguments['client_id'][0].strip()
        contacts = self.application.contacts

        # XXX: make sure client id is a 64 long key
        tox = self.application.tox
        if 'add' in self.request.body_arguments:

            # in that context client_id can be an e-mail or a client_id
            try:
                rclient_id = user_lookup(client_id)
            except ValueError, e:
                print str(e)
                session['alert'] = str(e)
                self.redirect('/')
                return

            if rclient_id != client_id:
                email = client_id
            else:
                email = client_id + '@tox'

            client_id = rclient_id

            try:
                tox.add_friend_norequest(client_id)
            except OperationFailedError, e:
                # XXX we want an error message
                print str(e)
                session['alert'] = str(e)
                self.redirect('/')
                return
            else:
                tox.save()

            friend_id = tox.get_friend_id(client_id)
            contact = {'friend_id': friend_id, 'client_id': client_id,
                       'relay': True}
            contacts.add(email, **contact)
            contacts.save()
        elif 'delete' in self.request.body_arguments:
            try:
                friend_id = tox.get_friend_id(client_id)
                tox.del_friend(friend_id)
            except OperationFailedError, e:
                print str(e)
            else:
                tox.save()

            contacts.delete_first(client_id=client_id)
            contacts.save()

        self.redirect('/')


application = tornado.web.Application([
    (r"/", DashboardHandler),
    (r"/relay", RelayHandler),
    (r"/friend", FriendHandler),
    (r"/friend/(.*)", FriendHandler)
])
