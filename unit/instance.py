import os
import logging
import socket
import time
import re
import json
import time

from subprocess import Popen


script_abspath = os.path.realpath(
    os.path.join(
        os.path.dirname(__file__), 'mock'
    )
)


class Instance:
    def __init__(self, console_sock, cluster_cookie):
        self.script = "init.lua"
        self.console_sock = console_sock
        self.cluster_cookie = cluster_cookie

        self.process = None
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    def start(self):
        command = [os.path.join(script_abspath, self.script)]

        env = os.environ.copy()
        env['TARANTOOL_CONSOLE_SOCK'] = self.console_sock
        self.process = Popen(command, env=env)

        logging.warning('PID %d', self.process.pid)

        time.sleep(0.2)

        self.sock.connect(self.console_sock)
        self.sock.recv(1024)

    def eval(self, func_body):
        def sendall(msg):
            return self.sock.sendall(msg.encode())

        def recvall():
            data = ''
            while True:
                chunk = self.sock.recv(1024).decode()
                # It is correct because of cmd structure: it always returns a value
                if chunk == '':
                    errmsg = 'Error: broken pipe. Probably, instance was not bootsrapped yet to perform this operation'
                    raise Exception(cartridge_errcodes.BROKEN_PIPE, errmsg)
                data = data + chunk
                if data.endswith('\n...\n'):
                    break
            return data

        cmd = '''
            local ok, ret = pcall(function()
                local function f()
                    {}
                end
                return f()
            end)
            ret = require("json").encode({{
                ok = ok,
                ret = ret or require("json").NULL,
            }})
            return string.hex(ret)
        '''.format(func_body)

        lines = [l.strip() for l in cmd.split('\n') if l.strip()]
        cmd = ' '.join(lines) + '\n'

        sendall(cmd)

        raw_output = recvall()

        hex_output = re.sub(r"^---\n-\s+?", '', raw_output)
        hex_output = re.sub(r"'?\n...\n$", '', hex_output)
        hex_output = re.sub(r"\n\s*", '', hex_output)

        output = bytearray.fromhex(hex_output).decode('utf-8')

        ret = json.loads(output)
        if not ret['ok']:
            errmsg = 'Error while running function: {}. (Function: {})'.format(ret['ret'], func_body)
            raise Exception(errmsg)

        return ret['ret']

    def set_membership_status(self, status):
        self.eval('''
            return require('membership').set_status('{}')
        '''.format(status))

    def stop(self):
        self.sock.close()
        if self.process is not None:
            self.process.kill()
            self.process.communicate()
