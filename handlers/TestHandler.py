#!/usr/bin/python
#-*- coding: utf-8 -*-
import time
import uuid
import traceback

import tornado.websocket


class EchoHandler(tornado.websocket.WebSocketHandler):
    clientId = None

    def check_origin(self, origin):
        return True

    def open(self):
        from WebSocketServer import WebsocketServer as wsServer
        self.clientId = str(uuid.uuid4())
        wsServer.clients[self.clientId] = self
        wsServer.log('WebSocket client has been registered : TotalClients=%d' % len(wsServer.clients), self.clientId)

    def data_received(self, chunk):
        from WebSocketServer import WebsocketServer as wsServer
        wsServer.log('Received data from WebSocket : Data=\'%s\'' % str(chunk), self.clientId)

    def on_message(self, message):
        from WebSocketServer import WebsocketServer as wsServer
        try:
            wsServer.log('Received message from WebSocket : Message=%s' % message, self.clientId)
            time.sleep(1)
            handler = wsServer.clients.get(self.clientId)
            ret_message = message+'[ECHO]'
            if handler:
                handler.write_message(ret_message)
                wsServer.log('Sent message to WebSocket client : Message=%s' % ret_message, self.clientId)
            else:
                wsServer.log('Not found client key in list. The client may be closed.', self.clientId)
        except Exception as e:
            traceback.print_exc()
            wsServer.log('Exception occurred during parsing received data : Exception=%s, Message=\"%s\"' % (e, message), self.clientId)

    def on_close(self):
        from WebSocketServer import WebsocketServer as wsServer
        if wsServer.clients.get(self.clientId):
            del wsServer.clients[self.clientId]
        wsServer.log('WebSocket client has been closed : TotalClients=%d' % len(wsServer.clients), self.clientId)

