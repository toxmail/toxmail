import os

import tornado.web
from tornado import template


loader = template.Loader(os.path.dirname(__file__))


class DashboardHandler(tornado.web.RequestHandler):
    def get(self):
        tox = self.application.tox
        client_id = tox.get_address()
        friends = []

        for friend_id in tox.get_friendlist():
            friend = {'friend_id': friend_id}
            friend['client_id'] = tox.get_client_id(friend_id)
            friends.append(friend)

        resp = loader.load("index.html").generate(client_id=client_id,
                                                  friends=friends)
        self.write(resp)


application = tornado.web.Application([
    (r"/", DashboardHandler),
])
