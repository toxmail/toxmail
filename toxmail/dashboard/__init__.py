import os
from collections import defaultdict

from beaker.session import Session
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
        config = self.application.config
        contacts = self.application.contacts
        my_client_id = tox.get_address()
        friends = []

        for friend_id in tox.get_friendlist():
            friend = {'friend_id': friend_id}
            client_id = tox.get_client_id(friend_id)
            friend['client_id'] = client_id
            contact = contacts.first(client_id=client_id)
            if contact is not None:
                friend['email'] = contact.get('email', '')
            else:
                friend['email'] = ''

            friends.append(friend)

        resp = loader.load("index.html").generate(client_id=my_client_id,
                                                  friends=friends,
                                                  config=config,
                                                  alert=session.get('alert'))
        self.write(resp)


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
            contact = {'friend_id': friend_id, 'client_id': client_id}
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
    (r"/friend", FriendHandler),
    (r"/friend/(.*)", FriendHandler)
])
