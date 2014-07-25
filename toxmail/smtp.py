from bonzo.server import SMTPServer as _SMTPServer
from pyzmail import PyzMessage


class SMTPServer(_SMTPServer):
    def _on_data(self, data):
        msg = PyzMessage.factory(payload)
        try:
            self.request_callback(msg)
        except Exception, e:
            print str(e)
            self.write("554 " + str(e))
        else:
            self.write("250 Ok")
