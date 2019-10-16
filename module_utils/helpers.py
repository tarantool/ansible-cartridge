#!/usr/bin/python

import socket
import json
import re


class ModuleRes:
    def __init__(self, success, msg=None, changed=False, meta=None):
        self.success = success
        self.msg = msg
        self.changed = changed
        self.meta = meta


class Console:
    def __init__(self, socket_path):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(socket_path)
        self.sock.recv(1024)

    def close(self):
        return self.sock.close()

    def eval(self, func_body):
        def sendall(msg):
            return self.sock.sendall(msg.encode())

        def recvall():
            data = []
            while True:
                chunk = self.sock.recv(1024).decode()
                data.append(chunk)
                if chunk.endswith('\n...\n'):
                    break
            return ''.join(data)
        cmd = '''
            function f()
                {}
            end
            local res = require("json").encode(f()):gsub([[\n]], [[\n!]])
            return res
        '''.format(func_body)

        lines = [l.strip() for l in cmd.split('\n') if l.strip()]
        cmd = ' '.join(lines) + '\n'
        sendall(cmd)

        raw_output = recvall()
        output = re.sub("^---\n- '", '', raw_output)
        output = re.sub("'\n...\n$", '', output)

        return json.loads(output.replace('\n ', '').replace('\n!', '\n'))  # XXX: fix it


def get_control_console(socket_path):
    return Console(socket_path)
