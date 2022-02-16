#!/usr/bin/python
#-*- coding: utf-8 -*-
import base64
import json
import os
import traceback
import uuid
import datetime
import stat
import binascii
import time
import platform

import tornado.web
import tornado.websocket

from util import FileInfo

my_init_path = None
os_type = platform.system()
init_path = {}
perm_path = {}
auth_tokens = {}
token_validity_sec = 60
if os_type == 'Windows':
    win_temp = os.getenv('TEMP').decode('cp949')
    win_prof = os.getenv('USERPROFILE').decode('cp949')
    dir_init = win_temp if my_init_path is None else my_init_path
    dirs_allow = [dir_init+os.sep, win_prof+os.sep, win_temp+os.sep]
    dirs_deny = [os.getenv('SystemDrive').decode('cp949')+os.sep]
else:
    dir_init = '/tmp' if my_init_path is None else my_init_path
    dirs_allow = [dir_init+os.sep, '/home/', '/tmp/']
    dirs_deny = ['/']
init_path[os_type] = dir_init
perm_path[os_type] = {'allow': dirs_allow, 'deny': dirs_deny}


def get_init_path():
    return init_path[os_type]

def check_permission(file_path):
    abs_path = os.path.abspath(file_path)
    for check_path in perm_path[os_type]['allow']:
        if abs_path[:len(check_path)] == check_path:
            return True
    for check_path in perm_path[os_type]['deny']:
        if abs_path[:len(check_path)] == check_path:
            return False
    return True

def generate_token(file_path):
    token = binascii.hexlify(os.urandom(32))
    info = [ file_path, int(time.time()) ]
    auth_tokens[token] = info
    return token

def check_token(file_path, token):
    for tok in auth_tokens.keys():
        auth_path, auth_time = auth_tokens[tok]
        time_diff_sec = int(time.time()) - auth_time
        if time_diff_sec >= token_validity_sec:
            del auth_tokens[tok]
    for tok in auth_tokens.keys():
        auth_path, auth_time = auth_tokens[tok]
        if token == tok and auth_path == file_path:
            return True
    return False

class FileHandler(tornado.websocket.WebSocketHandler):
    clientId = None
    fileObj = None
    stopFlag = False

    def check_origin(self, origin):
        return True

    def open(self):
        from WebSocketServer import WebsocketServer as wsServer
        self.clientId = str(uuid.uuid4())
        wsServer.clients[self.clientId] = self
        wsServer.log('WebSocket client has been registered : TotalClients=%d' % len(wsServer.clients), self.clientId)

    def data_received(self, chunk):
        from WebSocketServer import WebsocketServer as wsServer
        wsServer.log('Received data from WebSocket : Size=%d' % len(chunk), self.clientId)

    def on_message(self, message):
        from WebSocketServer import WebsocketServer as wsServer
        try:
            if message[0:3] == '--@':
                wsServer.log('Received message from WebSocket : Message=\"%s\"' % message, self.clientId)
            else:
                wsServer.log('Received message from WebSocket : Size=%d' % len(message), self.clientId)
            handler = wsServer.clients.get(self.clientId)
            if handler:
                handler._process_message(message)
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

    def _process_message(self, message):
        from WebSocketServer import WebsocketServer as wsServer
        if message[:7] == '--@init':
            self.write_message('--@init:#dir#:%s' % get_init_path())
        elif message[:18] == '--@upload:#begin#:':
            filename_org = message[18:].encode('utf-8')
            filename = filename_org
            idx = 1
            while os.path.exists(filename):
                filename = filename_org + '(%d)'%idx
                idx += 1
            try:
                self.fileObj = open(filename, 'wb')
                self.stopFlag = False
                self.write_message('--@upload:#ready#:%s' % self.fileObj.name)
                wsServer.log('Started to upload the file: path=%s' % self.fileObj.name, self.clientId)
            except BaseException as e:
                self.write_message('--@upload:#error#:%s' % str(e))
        elif message[:21] == '--@upload:#begin.ow#:':
            filename = message[21:].encode('utf-8')
            try:
                self.fileObj = open(filename, 'w')
                self.stopFlag = False
                self.write_message('--@upload:#ready#:%s' % self.fileObj.name)
                wsServer.log('Started to upload the file: path=%s' % self.fileObj.name, self.clientId)
            except BaseException as e:
                self.write_message('--@upload:#error#:%s' % str(e))
        elif message[:18] == '--@upload:#cancel#':
            self.stopFlag = True
            if self.fileObj is not None:
                wsServer.log('Received request to stop uploading: path=%s' % self.fileObj.name, self.clientId)
        elif message == '--@upload:#end#':
            if self.fileObj is not None:
                self.fileObj.close()
                filesize = os.path.getsize(self.fileObj.name)
                self.write_message('--@upload:#finish#:%d' % filesize)
                wsServer.log('Finished to upload the file: path=%s, size=%d' % (self.fileObj.name, filesize), self.clientId)
                self.fileObj = None
        elif message[:10] == '--@delete:':
            filename = message[10:].encode('utf-8')
            abs_path = os.path.abspath(filename)
            if os.path.exists(filename):
                if not check_permission(filename):
                    self.write_message('--@delete:#deny#:%s' % abs_path)
                elif os.path.isdir(filename):
                    self.write_message('--@delete:#directory#:%s' % abs_path)
                else:
                    try:
                        os.remove(filename)
                        self.write_message('--@delete:#finish#:%s' % abs_path)
                        wsServer.log('Deleted the file: path=%s' % abs_path, self.clientId)
                    except BaseException as e:
                        self.write_message('--@delete:#error#:%s' % str(e))
            else:
                self.write_message('--@delete:#not_exists#:%s' % abs_path)
        elif message[:8] == '--@list:':
            dirname = message[8:].encode('utf-8')
            abs_path = os.path.abspath(dirname)
            if dirname != abs_path:
                self.write_message('--@list:#dir#:%s' % abs_path)
            if os.path.exists(dirname):
                if not check_permission(dirname+os.sep+'dummy'):
                    self.write_message('--@list:#deny#:%s' % abs_path)
                elif os.path.isfile(dirname):
                    self.write_message('--@list:#file#:%s' % abs_path)
                else:
                    try:
                        filelist_dict = FileInfo.get_file_info(abs_path, include_current_and_parent_dir=True)
                        filelist = json.dumps(filelist_dict, encoding='utf-8')
                        filelist_enc = base64.b64encode(str(filelist))
                        self.write_message('--@list:#finish#:%s' % filelist_enc)
                        wsServer.log('Return file list: path=%s' % abs_path, self.clientId)
                    except BaseException as e:
                        self.write_message('--@list:#error#:%s' % str(e))
            else:
                self.write_message('--@list:#not_exists#:%s' % abs_path)
        else:
            if self.stopFlag:
                fileSize = os.path.getsize(self.fileObj.name)
                wsServer.log('Stopping uploading the file : path=%s, size=%d' % (self.fileObj.name, fileSize), self.clientId)
                self.write_message('--@upload:#cancel#:%d' % fileSize)
                self.fileObj.close()
                self.fileObj = None
                self.stopFlag = False
            elif self.fileObj is not None:
                try:
                    self.fileObj.write(message)
                    wsServer.log('Wrote the message to file : path=%s, size=%d' % (self.fileObj.name, len(message)), self.clientId)
                    self.write_message('--@upload:#continue#:%d' % len(message))
                except BaseException as e:
                    self.write_message('--@upload:#error#:%s' % str(e))
                    self.fileObj.close()
                    self.fileObj = None
                    self.stopFlag = False


class DownloadHandler(tornado.web.RequestHandler):
    root = None

    def initialize(self, path='/', default_filename=None):
        self.root = path
        self.default_filename = default_filename
 
    def head(self, path):
        self.get(path, include_body=False)
 
    def get(self, path, include_body=True):
        from WebSocketServer import WebsocketServer as wsServer
        abspath = os.path.abspath(os.path.join(self.root, path)).encode('utf-8')
        token = self.get_argument('token', '')
        wsServer.log('Requested to download the file: path=%s' % abspath)

        # os.path.abspath strips a trailing /
        # it needs to be temporarily added back for requests to root/
        if os_type == 'Linux' and not (abspath + os.path.sep).startswith(self.root):
            raise tornado.web.HTTPError(403, '%s is not in root static directory', path)
        elif os_type == 'Windows' and abspath[1:3] != ':\\':
            raise tornado.web.HTTPError(403, '%s is not in root static directory', path)
        if os.path.isdir(abspath) and self.default_filename is not None:
            # need to look at the request.path here for when path is empty
            # but there is some prefix to the path that was already
            # trimmed by the routing
            if not self.request.path.endswith('/'):
                self.redirect(self.request.path + '/')
                return
            abspath = os.path.join(abspath, self.default_filename)
        if not os.path.exists(abspath):
            raise tornado.web.HTTPError(404)
        if not os.path.isfile(abspath):
            raise tornado.web.HTTPError(403, '%s is not a file', path)
        if not check_permission(abspath):
            raise tornado.web.HTTPError(403, 'Permission(path) denied.')
        if not check_token(abspath, token):
            raise tornado.web.HTTPError(403, 'Permission(token) denied.')

        stat_result = os.stat(abspath)
        modified = datetime.datetime.fromtimestamp(stat_result[stat.ST_MTIME])
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', 'attachment; filename=%s' % os.path.basename(abspath).encode('cp949'))
        self.set_header('Content-Transfer-Encoding', 'binary');
        self.set_header('Last-Modified', modified)

        if not include_body:
            return
        else:
            wsServer.log('Started to download the file: path=%s, size=%d' % (abspath, os.path.getsize(abspath)))
            self._write_file(abspath)
            wsServer.log('Finished to download the file: path=%s, size=%d' % (abspath, os.path.getsize(abspath)))
 
    def _write_file(self, path):
        for chunk in self._read_chunk(path):
            self.write(chunk)

    def _read_chunk(self, path, chunk_size=8192): 
        with open(path, 'rb') as f: 
            while True: 
                chunk = f.read(chunk_size) 
                if chunk: 
                    yield chunk 
                else: 
                    return


class TokenHandler(tornado.web.RequestHandler):
    def get(self, path):
        from WebSocketServer import WebsocketServer as wsServer
        filepath = self.get_argument('filepath', '')
        abspath = os.path.abspath(filepath).encode('utf-8')
        wsServer.log('Requested to get auth token for download the file: path=%s' % abspath)

        if not os.path.exists(abspath):
            raise tornado.web.HTTPError(403, '%s does not exists', path)
        if not os.path.isfile(abspath):
            raise tornado.web.HTTPError(403, '%s is not a file', path)
        if not check_permission(abspath):
            raise tornado.web.HTTPError(403, 'Permission denied.')

        token = generate_token(abspath)
        self.set_header('Content-Type', 'application/json; charset=utf-8')
        ret_dict = {'path': abspath, 'validity': token_validity_sec, 'token': token}
        self.write(json.dumps(ret_dict, encoding='utf-8'))
        wsServer.log('Generated auth token for download the file: path=%s, token=%s' % (abspath, token))
 
