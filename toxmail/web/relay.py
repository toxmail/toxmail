import tornado.web
from toxmail.web.dashboard import DashboardHandler
from toxmail.web.dashboard import FriendHandler


class RelayHandler(DashboardHandler):
    template = 'relay.html'


application = tornado.web.Application([
    (r"/", RelayHandler),
    (r"/friend", FriendHandler),
    (r"/friend/(.*)", FriendHandler)
])
