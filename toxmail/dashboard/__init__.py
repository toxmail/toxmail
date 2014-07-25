import os

import tornado.web
from tornado import template


loader = template.Loader(os.path.dirname(__file__))


class DashboardHandler(tornado.web.RequestHandler):
    def get(self):
        tox_id = self.application.tox.get_address()
        resp = loader.load("index.html").generate(tox_id=tox_id)
        self.write(resp)


application = tornado.web.Application([
    (r"/", DashboardHandler),
])
