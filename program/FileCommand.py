#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Requirements : python 2.7
Packages     : websocket-client 0.59.0, requests 2.27.1
               $ pip2 install websocket-client requests
"""

import os
import base64
import json
import ssl
import websocket
import requests
import urllib
import sys

domain = None
username = None
password = None
curr_dir = None


def on_message(ws, message):
    print("< {}".format(message))


def on_error(error):
    print("Error: {}".format(error))


def on_close(ws):
    print("Connection closed.")


def on_open(ws):
    print("Connection opened.")


def send_message(ws, message, verbose=True):
    if verbose:
        print("> {}".format(message))
    ws.send(message)


def send_binary(ws, content):
    ws.send(content, opcode=websocket.ABNF.OPCODE_BINARY)


def recv_message(ws, verbose=True):
    result = ws.recv()
    if result and verbose:
        on_message(ws, result)
    return result


def init(ws):
    global curr_dir
    send_message(ws, "--@init", False)
    result = recv_message(ws, False).split(':')
    if result[1] == "#dir#":
        curr_dir = result[-1]
        print("Current Directory: {}".format(curr_dir))
    else:
        print("Error")


def change_dir(ws):
    global curr_dir
    print("Current Directory: {}".format(curr_dir))
    temp_dir = raw_input("Enter the path of the directory to change: ").strip()
    if temp_dir is not "":
        temp_dir = (curr_dir + '/' + temp_dir) if '/' not in temp_dir and '\\' not in temp_dir else temp_dir
        send_message(ws, "--@list:{}".format(temp_dir), False)
        result = recv_message(ws, False).split(':')
        if result[1] == "#finish#":
            curr_dir = temp_dir
            print("Current Directory: {}".format(curr_dir))
        else:
            print("Error")


def list_file(ws):
    global curr_dir
    send_message(ws, "--@list:{}".format(curr_dir), False)
    result = recv_message(ws, False).split(':')
    if result[1] == "#finish#":
        files = json.loads(base64.b64decode(result[2]), encoding='utf-8')
        list_d = list(filter(lambda f: f["type"] == "D" and f["name"] != "." and f["name"] != "..", files))
        list_f = list(filter(lambda f: f["type"] == "F", files))
        cnt = 0
        if len(list_d) > 0:
            print("# Directories")
            for f in list_d:
                print(f["name"])
                cnt += 1
        if len(list_f) > 0:
            print("# Files")
            for f in list_f:
                print("{} [{}]".format(f["name"], f["size"]))
                cnt += 1
        if cnt == 0:
            print("Nothing to list.")
    else:
        print("Error")


def upload_file(ws):
    global curr_dir
    name = raw_input("Enter the absolute path of the file to upload: ").strip()
    if name is not "":
        overwrite = raw_input("Enter 'Y' to overwrite the file if it exists: ")
        overwrite = ".ow" if overwrite == "Y" else ""
        with open(unicode(name), "rb") as f:
            dir, file = os.path.split(name)
            send_message(ws, "--@upload:#begin{}#:{}".format(overwrite, curr_dir+'/'+file), False)
            result = recv_message(ws, False).split(':')
            if result[1] == "#ready#":
                dir, file = os.path.split(result[2])
                while True:
                    data = f.read(1024*1024)
                    if not data:
                        break
                    sys.stdout.write('.')
                    send_binary(ws, data)
                    result = recv_message(ws, False).split(':')
                    if result[1] == "#continue#":
                        continue
                    else:
                        print("Error wile uploading")
                        break
                print
                send_message(ws, "--@upload:#end#", False)
                result = recv_message(ws, False).split(':')
                if result[1] == "#finish#":
                    print("Successfully uploaded the file: {}".format(curr_dir+'/'+file))
                else:
                    print("Error: " + result[2])
            else:
                print("Error: " + result[2])


def download_file(ws):
    global curr_dir
    name = raw_input("Enter the file to download: ").strip()
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    if name is not "":
        dir_quote = urllib.quote(curr_dir)
        file_quote = urllib.quote(name)
        url = 'https://' + domain + '/securefile/ws/token?filepath=' + dir_quote + '/' + file_quote
        response = requests.get(url, auth=(username, password), verify=False)
        if response.status_code == 200:
            token = json.loads(response.text)["token"]
        url = 'https://' + domain + '/securefile/ws/download/' + dir_quote + '/' + file_quote + "?token=" + token
        response = requests.get(url, auth=(username, password), verify=False)
        if response.status_code == 200:
            with open(unicode(name), "wb") as f:
                f.write(response.content)
            print("Successfully downloaded the file: {}".format(os.getcwd()+os.sep+name))
        else:
            print("Error")


def delete_file(ws):
    global curr_dir
    name = raw_input("Enter the file to delete: ").strip()
    if name is not "":
        filename = curr_dir + '/' + name
        send_message(ws, "--@delete:{}".format(filename), False)
        result = recv_message(ws, False).split(':')
        if result[1] == "#finish#":
            print("Successfully deleted the file: {}".format(curr_dir + '/' + name))
        else:
            print("Error")


if __name__ == "__main__":
    reload(sys)
    sys.setdefaultencoding('utf-8')
    domain = raw_input("Enter domain or ip-address of server: ").strip()
    wss_url = "wss://{}/securefile/ws/file".format(domain)

    username = raw_input("Enter basic auth username: ")
    password = raw_input("Enter basic auth password: ")
    basic_auth = base64.b64encode("{}:{}".format(username, password))
    headers = ["Authorization: Basic {}".format(basic_auth)]
    sslopts = {"cert_reqs": ssl.CERT_NONE}

    ws = websocket.create_connection(wss_url, header=headers, sslopt=sslopts)
    on_open(ws)

    init(ws)
    while True:
        print
        command = raw_input("Enter command(cd, list, upload, download, delete, exit): ").strip()
        command = command.lower()

        try:
            if command == "cd":
                change_dir(ws)
            elif command == "list":
                list_file(ws)
            elif command == "upload":
                upload_file(ws)
            elif command == "download":
                download_file(ws)
            elif command == "delete":
                delete_file(ws)
            elif command == "exit":
                break
            else:
                if command is not None and command is not "":
                    print("Unknown command '{}'".format(command))
        except BaseException as e:
            print("Error occurred while executing command: " + str(e))
            if "Broken pipe" in str(e) or "already closed" in str(e):
                ws = websocket.create_connection(wss_url, header=headers, sslopt=sslopts)

    on_close(ws)
