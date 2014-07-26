import os

import tornado.web
from tornado import template
from tox import OperationFailedError


loader = template.Loader(os.path.dirname(__file__))


class DashboardHandler(tornado.web.RequestHandler):
    def get(self):
        tox = self.application.tox
        config = self.application.config
        client_id = tox.get_address()
        friends = []

        for friend_id in tox.get_friendlist():
            friend = {'friend_id': friend_id}
            friend['client_id'] = tox.get_client_id(friend_id)
            friends.append(friend)

        resp = loader.load("index.html").generate(client_id=client_id,
                                                  friends=friends,
                                                  config=config)
        self.write(resp)


class FriendHandler(tornado.web.RequestHandler):
    def post(self):
        client_id = self.request.body_arguments['client_id'][0].strip()
        # XXX: make sure client id is a 64 long key
        tox = self.application.tox

        if 'add' in self.request.body_arguments:
            try:
                tox.add_friend_norequest(client_id)
            except OperationFailedError:
                # XXX we want an error message
                pass
            else:
                tox.save()
        elif 'delete' in self.request.body_arguments:
            friend_id = tox.get_friend_id(client_id)
            tox.del_friend(friend_id)
            tox.save()

        self.redirect('/')


application = tornado.web.Application([
    (r"/", DashboardHandler),
    (r"/friend", FriendHandler),
    (r"/friend/(.*)", FriendHandler)
])
