#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Requirements : python 3
Packages     : websocket-client 1.3.1, requests 2.27.1
               $ pip install websocket-client requests
"""

import os
import base64
import json
import ssl
import websocket
import requests
import urllib.parse
import sys
import getpass

domain = None
username = None
password = None
curr_dir = None


def on_message(message):
    print("< {}".format(message))


def on_error(error):
    print("Error: {}".format(error))


def on_close():
    ws.close()
    print("Connection closed.")


def on_open():
    print("Connection opened.")


def send_message(message, verbose=True):
    if verbose:
        print("> {}".format(message))
    ws.send(message)


def send_binary(content):
    ws.send(content, opcode=websocket.ABNF.OPCODE_BINARY)


def recv_message(verbose=True):
    result = ws.recv()
    if result and verbose:
        on_message(result)
    return result


def join_paths(curr_dir, sub_dir):
    if '/' in curr_dir:
        return curr_dir + '/' + sub_dir
    elif '\\' in curr_dir:
        return curr_dir + '\\' + sub_dir
    else:
        return os.path.join(curr_dir, sub_dir)


def get_absolute_path(path):
    if path[0] != '/' and path[0] != '\\' and path[1] != ':':
        raise BaseException('Relative path is not allowed.')
    is_unix_format = False if path[1] == ':' else True
    temp_path = path.replace('\\', '/') if is_unix_format else path.replace('/', '\\')
    if os.name == 'nt' and is_unix_format:
        return os.path.abspath(temp_path)[2:].replace('\\', '/')
    elif os.name != 'nt' and not is_unix_format:
        print(temp_path)
        drive = temp_path[:2]
        tail = temp_path[2:]
        return drive + os.path.abspath(tail.replace('\\', '/')).replace('/', '\\')
    else:
        return os.path.abspath(temp_path)


def init():
    global curr_dir
    send_message("--@init", False)
    result = get_result_list(recv_message(False))
    if result[1] == "#dir#":
        curr_dir = result[-1]
        print("Current Directory: {}".format(curr_dir))
    else:
        print("Error : " + result[1])


def get_result_list(message):
    split_list = message.split(':')
    last_element = ":".join(split_list[2:])
    result = split_list[:2]
    result.append(last_element)
    return result


def change_dir():
    global curr_dir
    print("Current Directory: {}".format(curr_dir))
    temp_dir = input("Enter the path of the directory to change: ").strip()
    if temp_dir != "":
        request_change_dir(temp_dir if os.path.isabs(temp_dir) else join_paths(curr_dir, temp_dir))


def request_change_dir(directory):
    global curr_dir
    directory = join_paths(curr_dir, directory) if '/' not in directory and '\\' not in directory else directory
    send_message("--@list:{}".format(directory), False)
    result = get_result_list(recv_message(False))
    if result[1] == "#dir#":
        result = get_result_list(recv_message(False))
    if result[1] == "#finish#":
        curr_dir = get_absolute_path(directory)
        print("Current Directory: {}".format(curr_dir))
    else:
        print("Error : " + result[1])


def list_file():
    global curr_dir
    send_message("--@list:{}".format(curr_dir), False)
    result = get_result_list(recv_message(False))
    if result[1] == "#dir#":
        result = get_result_list(recv_message(False))
    if result[1] == "#finish#":
        files = json.loads(base64.b64decode(result[2]))
        list_d = list(filter(lambda f_item: f_item["type"] == "D" and f_item["name"] != "." and f_item["name"] != "..", files))
        list_f = list(filter(lambda f_item: f_item["type"] == "F", files))
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
        print("Error : " + result[1])


def upload_file():
    global curr_dir
    name = input("Enter the absolute path of the file to upload: ").strip()
    name = os.path.abspath(name)
    if not os.path.isfile(name):
        print("Only file type is allowed.")
    elif name != "":
        overwrite = input("Enter 'Y' to overwrite the file if it exists: ")
        overwrite = ".ow" if overwrite == "Y" else ""
        with open(name, "rb") as f:
            directory, file = os.path.split(name)
            send_message("--@upload:#begin{}#:{}".format(overwrite, join_paths(curr_dir, file)), False)
            result = get_result_list(recv_message(False))
            if result[1] == "#ready#":
                directory, file = os.path.split(result[2])
                while True:
                    data = f.read(1024*1024)
                    if not data:
                        break
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    send_binary(data)
                    result = get_result_list(recv_message(False))
                    if result[1] == "#continue#":
                        continue
                    else:
                        print("Error : Unexpected status " + result[1])
                        break
                print()
                send_message("--@upload:#end#", False)
                result = get_result_list(recv_message(False))
                if result[1] == "#finish#":
                    print("Successfully uploaded the file: {}".format(join_paths(curr_dir, file)))
                else:
                    print("Error: " + result[2])
            else:
                print("Error: " + result[2])


def download_file():
    global curr_dir
    name = input("Enter the file to download: ").strip()
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    if "\\" in name or "/" in name:
        print("The file name must not include a path. Move the directory first.")
    elif name != "":
        abspath = get_absolute_path(join_paths(curr_dir, name))
        url = 'https://' + domain + '/securefile/ws/token'
        response = requests.post(url, data={'filepath': abspath}, auth=(username, password), verify=False)
        if response.status_code == 200:
            token = json.loads(response.text)["token"]
        else:
            print("Error(Token): " + str(response.status_code))
            return
        url = 'https://' + domain + '/securefile/ws/download'
        response = requests.post(url, data={'filepath': abspath, 'token': token}, auth=(username, password), verify=False)
        if response.status_code == 200:
            with open(name, "wb") as f:
                f.write(response.content)
            print("Successfully downloaded the file: {}".format(os.getcwd()+os.sep+name))
        else:
            print("Error(Download): " + str(response.status_code))


def delete_file():
    global curr_dir
    name = input("Enter the file to delete: ").strip()
    if "\\" in name or "/" in name:
        print("The file name must not include a path. Move the directory first.")
    elif name != "":
        filename = join_paths(curr_dir, name)
        send_message("--@delete:{}".format(filename), False)
        result = get_result_list(recv_message(False))
        if result[1] == "#finish#":
            print("Successfully deleted the file: {}".format(join_paths(curr_dir, name)))
        else:
            print("Error : " + result[1])


if __name__ == "__main__":
    domain = input("Enter domain or ip-address of server: ").strip()
    wss_url = "wss://{}/securefile/ws/file".format(domain)

    username = input("Enter basic auth username: ")
    password = getpass.getpass("Enter basic auth password: ")
    basic_auth = base64.b64encode("{}:{}".format(username, password).encode('utf-8'))
    headers = ["Authorization: Basic {}".format(basic_auth.decode('utf-8'))]
    sslopts = {"cert_reqs": ssl.CERT_NONE}

    ws = websocket.create_connection(wss_url, header=headers, sslopt=sslopts)
    on_open()

    init()
    command = None
    while True:
        print()
        if command is None:
            command = input("Enter command(cd, list, upload, download, delete, exit): ").strip()
            command = command.lower()

        try:
            if command == "cd":
                change_dir()
            elif command == "list":
                list_file()
            elif command == "upload":
                upload_file()
            elif command == "download":
                download_file()
            elif command == "delete":
                delete_file()
            elif command == "exit":
                break
            else:
                if command is not None and command != "":
                    print("Error : Unknown command '{}'".format(command))
            command = None
        except BaseException as e:
            print("Error : Exception occurred while executing command: " + str(e))
            if "Broken pipe" in str(e) or "already closed" in str(e) or "10053" in str(e):
                ws = websocket.create_connection(wss_url, header=headers, sslopt=sslopts)
                print("Reconnected to server. Retrying the command...")
            else:
                command = None

    on_close()
