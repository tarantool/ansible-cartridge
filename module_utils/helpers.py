#!/usr/bin/python

import json
import os
import re
import socket
import textwrap

from ansible.module_utils.basic import AnsibleModule

DEFAULT_RUN_DIR = '/var/run/tarantool'
DEBUG_MESSAGES = []


# To print any string or object using warnings, you just need to call this function:
# helpers.debug('my_str')
# helpers.debug({'my_dict': ['str', 2]})
# In this case, you get the following output:
# [WARNING]: [001]: my_str
# [WARNING]: [002]: {
# [WARNING]: [003]:   "my_dict": [
# [WARNING]: [004]:     "str",
# [WARNING]: [005]:     2
# [WARNING]: [007]:   ]
# [WARNING]: [008]: }

# Also you can specify a string key to print it before each output line:
# helpers.debug('my_str', key='test_1')
# helpers.debug({'my_dict': ['str', 2]}, 'test_2')
# In this case, you get the following output:
# [WARNING]: [001]: [test_1]: my_str
# [WARNING]: [002]: [test_2]: {
# [WARNING]: [003]: [test_2]:   "my_dict": [
# [WARNING]: [004]: [test_2]:     "str",
# [WARNING]: [005]: [test_2]:     2
# [WARNING]: [006]: [test_2]:   ]
# [WARNING]: [007]: [test_2]: }

def debug(value, key=None):
    global DEBUG_MESSAGES

    if type(value) != str:
        value = json.dumps(value, indent=2)
    value = value.split('\n')
    if key:
        value = map(lambda v: '[%s]: %s' % (key, v), value)

    # We should add line numbers because Ansible removes the same warnings.
    # So, for example, some `}` characters from a JSON object will not be printed.
    last_line = len(DEBUG_MESSAGES) + 1
    value = map(lambda v: '[%03d]: %s' % (last_line + v[0], v[1]), enumerate(value))

    DEBUG_MESSAGES += value


class ModuleRes:
    def __init__(self, failed=False, changed=True, msg=None, exception=None, warnings=None, fact=None, **kwargs):
        self.failed = failed
        self.changed = changed
        self.warnings = warnings
        self.fact = fact
        self.kwargs = kwargs

        self.msg = None
        if msg:
            self.failed = True
            self.msg = str(msg)
        if exception:
            self.failed = True
            self.msg = str(exception)

    def get_exit_json(self):
        res = {}

        if not self.failed:
            res['changed'] = self.changed

        if self.msg is not None:
            res['msg'] = self.msg

        if self.fact is not None:
            res['fact'] = self.fact

        if self.warnings is None:
            self.warnings = []
        self.warnings += DEBUG_MESSAGES
        res['warnings'] = self.warnings

        for key, value in self.kwargs.items():
            res[key] = value

        return res

    def exit(self, module):
        if not self.failed:
            module.exit_json(**self.get_exit_json())
        else:
            module.fail_json(**self.get_exit_json())


def execute_module(argument_spec, function):
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = function(module.params)
    except Exception as e:
        res = ModuleRes(exception=e)
    res.exit(module)


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
dynamic_box_cfg_params = {
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
}

memory_size_box_cfg_params = {
    'memtx_memory',
    'vinyl_memory',
}


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

        cmd_fmt = textwrap.dedent('''
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
        ''')

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


def is_expelled(host_vars):
    return host_vars.get('expelled') is True


def is_stateboard(host_vars):
    return host_vars.get('stateboard') is True


def get_instance_id(app_name, instance_name=None, stateboard=False):
    if stateboard:
        return '%s-stateboard' % app_name

    if instance_name is None:
        raise Exception("instance_name should be not none for non-stateboard instance")

    return '%s.%s' % (app_name, instance_name)


def get_instance_console_sock(run_dir, app_name, instance_name=None, stateboard=False):
    instance_fullname = get_instance_id(app_name, instance_name, stateboard)
    return os.path.join(run_dir, '%s.control' % instance_fullname)


def get_instance_pid_file(run_dir, app_name, instance_name=None, stateboard=False):
    instance_id = get_instance_id(app_name, instance_name, stateboard)
    return os.path.join(run_dir, '%s.pid' % instance_id)


def get_instance_dir(data_dir, app_name, instance_name=None, stateboard=False):
    instance_id = get_instance_id(app_name, instance_name, stateboard)
    return os.path.join(data_dir, instance_id)


def get_multiversion_instance_code_dir(instances_dir, app_name, instance_name=None, stateboard=False):
    instance_id = get_instance_id(app_name, instance_name, stateboard)
    return os.path.join(instances_dir, instance_id)


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
