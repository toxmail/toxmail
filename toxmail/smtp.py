from bonzo.server import SMTPServer as _SMTPServer
from bonzo.server import SMTPConnection as _SMTPConnection
from pyzmail import PyzMessage


class SMTPServer(_SMTPServer):
    def handle_stream(self, stream, address):
        SMTPConnection(stream, address, self.request_callback)


class SMTPConnection(_SMTPConnection):
    def _on_data(self, data):
        data = str(data)
        msg = PyzMessage.factory(data)
        try:
            self.request_callback(msg)
        except Exception, e:
            print str(e)
            self.write("554 " + str(e))
        else:
            self.write("250 Ok")
