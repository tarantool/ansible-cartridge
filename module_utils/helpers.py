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


class CartridgeException(Exception):
    pass


class Console:
    def __init__(self, socket_path):
        if not os.path.exists(socket_path):
            errmsg = 'Instance socket not found: "{}". '.format(socket_path) + \
                'Make sure instance was started correctly'
            raise CartridgeException(errmsg)

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        try:
            self.sock.connect(socket_path)
        except socket.error as socket_err:
            errmsg = 'Failed to connect to socket "{}": {}'.format(socket_path, socket_err)
            raise CartridgeException(errmsg)

        self.sock.recv(1024)

    def close(self):
        return self.sock.close()

    def eval(self, func_body):
        def sendall(msg):
            return self.sock.sendall(msg.encode())

        def recvall():
            data = ''
            while True:
                chunk = self.sock.recv(1024).decode()
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

        output = bytearray.fromhex(hex_output).decode('utf-8')

        ret = json.loads(output)
        if not ret['ok']:
            raise CartridgeException('Error while running function: {}. (Function: {})'.format(ret['ret'], func_body))

        return ret['ret']


def get_control_console(socket_path):
    return Console(socket_path)


def get_all_cluster_instances(control_console):
    servers = control_console.eval('''
        local instances = require('cartridge').admin_get_servers()
        local res = {}
        for _, i in ipairs(instances) do
            local replicaset = require('json').NULL
            if i.replicaset then
                replicaset = {
                    uuid = i.replicaset.uuid,
                    alias = i.replicaset.alias,
                    roles = i.replicaset.roles,
                }
            end
            table.insert(res, {
                uuid = i.uuid,
                uri = i.uri,
                alias = i.alias,
                status = i.status,
                replicaset = replicaset,
            })
        end
        return res
    ''')

    return servers


def instance_expelled(host_vars):
    return 'expelled' in host_vars and host_vars['expelled']
