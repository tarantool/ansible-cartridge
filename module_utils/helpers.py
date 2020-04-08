#!/usr/bin/python

import socket
import json
import re
import os


class ModuleRes:
    def __init__(self, success, msg=None, changed=False, meta=None):
        self.success = success
        self.msg = msg
        self.changed = changed
        self.meta = meta


class CartridgeErrorCodes:
    def __init__(self):
        self.SOCKET_NOT_FOUND = 'SOCKET_NOT_FOUND'
        self.FAILED_TO_CONNECT_TO_SOCKET = 'FAILED_TO_CONNECT_TO_SOCKET'
        self.INSTANCE_IS_NOT_STARTED_YET = 'INSTANCE_IS_NOT_STARTED_YET'
        self.BROKEN_PIPE = 'BROKEN_PIPE'
        self.FUNCTION_ERROR = 'FUNCTION_ERROR'
        self.MISSED_SECTION = 'MISSED_SECTION'


cartridge_errcodes = CartridgeErrorCodes()


class CartridgeException(Exception):
    def __init__(self, code, message):
        super(CartridgeException, self).__init__(message)
        self.code = code


class Console:
    def __init__(self, socket_path):
        self.sock = None

        if not os.path.exists(socket_path):
            errmsg = 'Instance socket not found: "{}". '.format(socket_path) + \
                'Make sure instance was started correctly'
            raise CartridgeException(cartridge_errcodes.SOCKET_NOT_FOUND, errmsg)

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        try:
            self.sock.connect(socket_path)
        except socket.error as socket_err:
            if socket_err.errno == 111:
                errmsg = 'Failed to connect to socket "{}": Instance is not started yet'.format(socket_path)
                raise CartridgeException(cartridge_errcodes.INSTANCE_IS_NOT_STARTED_YET, errmsg)
            errmsg = 'Failed to connect to socket "{}": {}'.format(socket_path, socket_err)
            raise CartridgeException(cartridge_errcodes.FAILED_TO_CONNECT_TO_SOCKET, errmsg)

        self.sock.recv(1024)

    def close(self):
        if self.sock is not None:
            self.sock.close()

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
                    raise CartridgeException(cartridge_errcodes.BROKEN_PIPE, errmsg)
                data = data + chunk
                if data.endswith('\n...\n'):
                    break
            return data

        cmd = '''
            local ok, ret = pcall(function()
                local function f()
                    require('fiber').self().storage.console = nil
                    {}
                end
                return f()
            end)
            ret = require("json").encode({{
                ok = ok,
                ret = ret,
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

        try:
            output = bytearray.fromhex(hex_output).decode('utf-8')
        except Exception:
            raise Exception(hex_output)

        ret = json.loads(output)
        if not ret['ok']:
            errmsg = 'Error while running function: {}. (Function: {})'.format(ret['ret'], func_body)
            raise CartridgeException(cartridge_errcodes.FUNCTION_ERROR, errmsg)

        return ret['ret']

    def __del__(self):
        self.close()


def get_control_console(socket_path):
    return Console(socket_path)


def get_all_cluster_instances(control_console):
    servers = control_console.eval('''
        local instances = require('cartridge').admin_get_servers()
        local res = {}
        for _, i in ipairs(instances) do
            local replicaset = box.NULL
            if i.replicaset then
                replicaset = {
                    uuid = i.replicaset.uuid or box.NULL,
                    alias = i.replicaset.alias or box.NULL,
                    roles = i.replicaset.roles or box.NULL,
                }
            end
            table.insert(res, {
                uuid = i.uuid or box.NULL,
                uri = i.uri or box.NULL,
                alias = i.alias or box.NULL,
                status = i.status or box.NULL,
                replicaset = replicaset,
            })
        end
        return res
    ''')

    return servers


def instance_expelled(host_vars):
    return 'expelled' in host_vars and host_vars['expelled']
