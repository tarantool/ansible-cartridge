#!/usr/bin/python

import socket
import json
import re
import os


class ModuleRes:
    def __init__(self, success, msg=None, changed=False, meta=None, warnings=[]):
        self.success = success
        self.msg = msg
        self.changed = changed
        self.meta = meta
        self.warnings = warnings


class CartridgeErrorCodes:
    def __init__(self):
        self.SOCKET_NOT_FOUND = 'SOCKET_NOT_FOUND'
        self.FAILED_TO_CONNECT_TO_SOCKET = 'FAILED_TO_CONNECT_TO_SOCKET'
        self.INSTANCE_IS_NOT_STARTED_YET = 'INSTANCE_IS_NOT_STARTED_YET'
        self.BROKEN_PIPE = 'BROKEN_PIPE'
        self.FUNCTION_ERROR = 'FUNCTION_ERROR'
        self.MISSED_SECTION = 'MISSED_SECTION'
        self.BAD_VALUE_TYPE = 'BAD_VALUE_TYPE'


cartridge_errcodes = CartridgeErrorCodes()


# parameters of instance configuration that can be changed dynamically
dynamic_box_cfg_params = set([
    'memtx_memory',
    'vinyl_memory',
    'custom_proc_title',
    'listen',
    'read_only',
    'sql_cache_size',
    'vinyl_timeout',
    'worker_pool_threads',
    'vinyl_cache',
    'checkpoint_interval',
    'checkpoint_count',
    'checkpoint_wal_threshold',
    'snap_io_rate_limit',
    'replication_connect_timeout',
    'replication_connect_quorum',
    'replication_skip_conflict',
    'replication_sync_lag',
    'replication_sync_timeout',
    'replication_timeout',
    'replication_synchro_quorum',
    'replication_synchro_timeout',
    'io_collect_interval',
    'net_msg_max',
    'readahead',
    'log_level',
    'too_long_threshold',
    'log_format',
    'feedback_enabled',
    'feedback_host',
    'feedback_interval',
])

memory_size_box_cfg_params = set([
    'memtx_memory',
    'vinyl_memory',
])


class CartridgeException(Exception):
    def __init__(self, code, message):
        super(CartridgeException, self).__init__(message)
        self.code = code


class Console:
    def __init__(self, socket_path):
        self.sock = None

        if not os.path.exists(socket_path):
            errmsg = 'Instance socket not found: "{}". '.format(socket_path) + \
                'Make sure the instance was started correctly'
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

    def eval(self, func_body, *args):
        def sendall(msg):
            return self.sock.sendall(msg.encode())

        def recvall():
            data = ''
            while True:
                chunk = self.sock.recv(1024).decode()
                # It is correct because of cmd structure: it always returns a value
                if chunk == '':
                    errmsg = 'Error: broken pipe. ' + \
                        'Probably, the instance was not bootstrapped yet to perform this operation'
                    raise CartridgeException(cartridge_errcodes.BROKEN_PIPE, errmsg)
                data = data + chunk
                if data.endswith('\n...\n'):
                    break
            return data

        if not args:
            args = []
        args_encoded = json.dumps(args)

        cmd_fmt = '''
local function func(...)
    {func_body}
end
local args = require('json').decode('{args_encoded}')
local ret = {{
    load(
        'local func, args = ... return func(unpack(args))',
        '@eval'
    )(func, args)
}}
return string.hex(require('json').encode(ret))
'''

        cmd = cmd_fmt.format(func_body=func_body, args_encoded=args_encoded)

        lines = [line.strip() for line in cmd.split('\n') if line.strip()]
        cmd = ' '.join(lines) + '\n'

        sendall(cmd)

        raw_output = recvall()

        hex_output = re.sub(r"^---\n-\s+?", '', raw_output)
        hex_output = re.sub(r"'?\n...\n$", '', hex_output)
        hex_output = re.sub(r"\n\s*", '', hex_output)

        if hex_output.startswith("error:"):
            err = re.sub(r"error:\s+", '', hex_output)
            raise CartridgeException(cartridge_errcodes.FUNCTION_ERROR, err)

        output = bytearray.fromhex(hex_output).decode('utf-8')

        data = json.loads(output)
        return data

    def eval_res_err(self, func_body, *args):
        data = self.eval(func_body, *args)

        assert len(data) <= 2

        if len(data) == 0:
            # return nil
            data.append(None)

        if len(data) == 1:
            # return res
            data.append(None)

        # return res, err

        # err can be tarantool/errors instance
        if isinstance(data[1], dict) and data[1].get('err') is not None:
            data[1] = data[1].get('err')

        return data

    def __del__(self):
        self.close()


def get_control_console(socket_path):
    return Console(socket_path)


def get_all_cluster_instances(control_console):
    data = control_console.eval('''
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

    return data[0]


def is_expelled(host_vars):
    return host_vars.get('expelled') is True


def is_stateboard(host_vars):
    return host_vars.get('stateboard') is True


def box_cfg_was_called(control_console):
    data = control_console.eval('''
        return type(box.cfg) ~= 'function'
    ''')
    return data[0]


def get_box_cfg(control_console):
    cfg, _ = control_console.eval_res_err('''
        return type(box.cfg) ~= 'function' and box.cfg or box.NULL
    ''')
    return cfg


def filter_none_values(d):
    return {
        k: v for k, v in d.items() if v is not None
    }
