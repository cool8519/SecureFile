#!/usr/bin/python
# -*- coding: utf-8 -*-
import datetime
import os
import signal
import sys

import tornado.httpserver
import tornado.ioloop
import tornado.web

from handlers import TestHandler, FileHandler


allowed_ip_list = set(['127.0.0.1'])


class WebsocketServer:
    clients = {}
    httpServer = None
    port = None

    def __init__(self, port):
        self.port = port

    def start(self):
        self.log('Starting the process : PID=%d' % os.getpid())
        self.httpServer = tornado.httpserver.HTTPServer(WebsocketApplication())
        self.httpServer.listen(self.port)
        self.log('Listening to the WebSocket server port : Port=%d' % self.port)
        try:
            tornado.ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            pass

    def stop(self, signum):
        self.log('WebsocketServer received signal : signum=%d' % signum)
        tornado.ioloop.IOLoop.instance().add_callback(tornado.ioloop.IOLoop.instance().stop)
        self.httpServer.close_all_connections()
        self.httpServer.stop()
        self.log('WebsocketServer was successfully stopped.')

    @staticmethod
    def log(msg, client_id=None):
        # type: (object, object) -> None
        if client_id is not None:
            print('[%s] [%s] %s' % (str(datetime.datetime.now()), client_id, msg))
        else:
            print('[%s] %s' % (str(datetime.datetime.now()), msg))


class SecurityChecker(tornado.web.RequestHandler):
    def prepare(self):
        if self.request.remote_ip not in allowed_ip_list:
            self.set_status(403)
            self.write("Access denied")
            self.finish()


class WebsocketApplication(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/ws/echo', TestHandler.EchoHandler),
            (r'/ws/file', FileHandler.FileHandler),
            (r'/ws/download', FileHandler.DownloadHandler),
            (r'/ws/token', FileHandler.TokenHandler),
        ]
        tornado.web.Application.__init__(self, handlers, default_handler_class=SecurityChecker)


if __name__ == '__main__':
    DEFAULT_PORT = 8080
    server_port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    server = WebsocketServer(port=server_port)
    signal.signal(signal.SIGINT, server.stop)
    server.start()
    WebsocketServer.log('End.')
