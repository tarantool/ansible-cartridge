#!/usr/bin/env python

import json
import os
import random
import re
import socket

from ansible.module_utils.basic import AnsibleModule

DEFAULT_RUN_DIR = '/var/run/tarantool'
TWOPHASE_OPTION_NAMES = ['netbox_call_timeout', 'upload_config_timeout', 'apply_config_timeout']

# parameters of instance configuration that can be changed dynamically
DYNAMIC_BOX_CFG_PARAMS = {
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

MEMORY_SIZE_BOX_CFG_PARAMS = {
    'memtx_memory',
    'vinyl_memory',
}

SYSTEM_CONFIG_SECTIONS = {
    'auth': True,
    'auth.yml': True,
    'topology': True,
    'topology.yml': True,
    'users_acl': True,
    'users_acl.yml': True,
    'vshard': True,
    'vshard.yml': True,
    'vshard_groups': True,
    'vshard_groups.yml': True,
}

FORMAT_REPLICASET_FUNC = '''
local cartridge_roles = require('cartridge.roles')
local function format_replicaset(r)
    local instances = {}
    for _, s in ipairs(r.servers) do
        if s.alias ~= nil then
            table.insert(instances, s.alias)
        end
    end

    return {
        uuid = r.uuid,
        alias = r.alias,
        enabled_roles = cartridge_roles.get_enabled_roles(r.roles),
        all_rw = r.all_rw,
        weight = r.weight,
        vshard_group = r.vshard_group,
        instances = instances,
    }
end
'''

FORMAT_SERVER_FUNC = '''
local function format_server(s)
    local replicaset_uuid
    if s.replicaset ~= nil then
        replicaset_uuid = s.replicaset.uuid
    end

    return {
        uuid = s.uuid,
        uri = s.uri,
        alias = s.alias,
        zone = s.zone,
        replicaset_uuid = replicaset_uuid,
    }
end
'''

FORMAT_SERVER_WITH_REPLICASET_INFO_FUNC = '''
local function format_server_with_replicaset_info(s)
    local replicaset_uuid
    local replicaset_alias
    if s.replicaset ~= nil then
        replicaset_uuid = s.replicaset.uuid
        replicaset_alias = s.replicaset.alias
    end

    return {
        uuid = s.uuid,
        alias = s.alias,
        priority = s.priority,
        status = s.status,
        replicaset_uuid = replicaset_uuid,
        replicaset_alias = replicaset_alias,
    }
end
'''

GET_REPLICASETS_FUNC_BODY = '''
%s

local replicasets = require('cartridge').admin_get_replicasets()
local ret = {}

for _, r in ipairs(replicasets) do
    if r.alias ~= nil then
        ret[r.alias] = format_replicaset(r)
    end
end

return ret
''' % FORMAT_REPLICASET_FUNC

GET_INSTANCES_FUNC_BODY = '''
%s

local servers = require('cartridge').admin_get_servers()
local ret = {}

for _, s in ipairs(servers) do
    if s.alias ~= nil then
        ret[s.alias] = format_server(s)
    end
end

return ret
''' % FORMAT_SERVER_FUNC

GET_INSTANCES_WITH_REPLICASETS_INFO_FUNC_BODY = '''
%s

local servers = require('cartridge').admin_get_servers()
local ret = {}

for _, s in ipairs(servers) do
    if s.alias ~= nil then
        ret[s.alias] = format_server_with_replicaset_info(s)
    end
end

return ret
''' % FORMAT_SERVER_WITH_REPLICASET_INFO_FUNC

SET_TWOPHASE_OPTIONS_FUNC_BODY = '''
local vars = require('cartridge.vars').new('cartridge.twophase')
if vars.options ~= nil then
    local options = ...
    for name, value in pairs(options) do
        vars.options[name] = value
    end
end
'''

READ_YAML_FILE_FUNC_BODY = '''
    local file_path = ...
    local file = require('fio').open(file_path)
    if file == nil then
        return nil, string.format("Failed to open YAML file: '%s'", file_path)
    end

    local buf = {}
    while true do
        local val = file:read(1024)
        if val == nil then
            return nil, string.format("Failed to read from YAML file: '%s'", file_path)
        elseif val == '' then
            break
        end
        table.insert(buf, val)
    end

    file:close()

    local data = table.concat(buf, '')

    local ok, result = pcall(require('yaml').decode, data)
    if not ok then
        return nil, string.format("Failed to decode YAML file: '%s'", file_path)
    end
    return result
'''

RANDOM_PREFIX = random.randint(1, 1000)
DEBUG_MESSAGES = []
WARNINGS = []


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
        self.warnings += WARNINGS
        self.warnings += DEBUG_MESSAGES
        res['warnings'] = self.warnings

        del WARNINGS[:]
        del DEBUG_MESSAGES[:]

        for key, value in self.kwargs.items():
            res[key] = value

        return res

    def exit(self, module):
        if not self.failed:
            module.exit_json(**self.get_exit_json())
        else:
            module.fail_json(**self.get_exit_json())


class CartridgeErrorCodes:
    SOCKET_NOT_FOUND = 'SOCKET_NOT_FOUND'
    FAILED_TO_CONNECT_TO_SOCKET = 'FAILED_TO_CONNECT_TO_SOCKET'
    INSTANCE_IS_NOT_STARTED_YET = 'INSTANCE_IS_NOT_STARTED_YET'
    BROKEN_PIPE = 'BROKEN_PIPE'
    FUNCTION_ERROR = 'FUNCTION_ERROR'
    MISSED_SECTION = 'MISSED_SECTION'
    BAD_VALUE_TYPE = 'BAD_VALUE_TYPE'


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
            raise CartridgeException(CartridgeErrorCodes.SOCKET_NOT_FOUND, errmsg)

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        try:
            self.sock.connect(socket_path)
        except socket.error as socket_err:
            if socket_err.errno == 111:
                errmsg = 'Failed to connect to socket "{}": Instance is not started yet'.format(socket_path)
                raise CartridgeException(CartridgeErrorCodes.INSTANCE_IS_NOT_STARTED_YET, errmsg)
            errmsg = 'Failed to connect to socket "{}": {}'.format(socket_path, socket_err)
            raise CartridgeException(CartridgeErrorCodes.FAILED_TO_CONNECT_TO_SOCKET, errmsg)

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
                    raise CartridgeException(CartridgeErrorCodes.BROKEN_PIPE, errmsg)
                data = data + chunk
                if data.endswith('\n...\n'):
                    break
            return data

        if not args:
            args = []
        args_encoded = json.dumps(args)

        func_body = func_body.replace("\n", "\\n").replace("'", "\\'")

        cmd_fmt = """
            local json = require('json')
            local net_box = require('net.box')
            local args = require('json').decode('{args_encoded}')
            local result = {{ net_box.self:eval('{func_body}', args) }}
            return string.hex(json.encode(result))
        """.replace('\n', ' ').strip()

        cmd = cmd_fmt.format(func_body=func_body, args_encoded=args_encoded)

        sendall(cmd + '\n')

        raw_output = recvall()

        hex_output = re.sub(r"^---\n-\s+?", '', raw_output)
        hex_output = re.sub(r"'?\n...\n$", '', hex_output)
        hex_output = re.sub(r"\n\s*", '', hex_output)

        if hex_output.startswith("error:"):
            err = re.sub(r"error:\s+", '', hex_output)
            raise CartridgeException(CartridgeErrorCodes.FUNCTION_ERROR, err)

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


def debug(value, key=None):
    # To print any string or object using warnings, you just need to call this function:
    # debug('my_str')
    # debug({'my_dict': ['str', 2]})
    # In this case, you get the following output:
    # [WARNING]: [001]: my_str
    # [WARNING]: [002]: {
    # [WARNING]: [003]:   "my_dict": [
    # [WARNING]: [004]:     "str",
    # [WARNING]: [005]:     2
    # [WARNING]: [007]:   ]
    # [WARNING]: [008]: }

    # Also you can specify a string key to print it before each output line:
    # debug('my_str', key='test_1')
    # debug({'my_dict': ['str', 2]}, 'test_2')
    # In this case, you get the following output:
    # [WARNING]: [001]: [test_1]: my_str
    # [WARNING]: [002]: [test_2]: {
    # [WARNING]: [003]: [test_2]:   "my_dict": [
    # [WARNING]: [004]: [test_2]:     "str",
    # [WARNING]: [005]: [test_2]:     2
    # [WARNING]: [006]: [test_2]:   ]
    # [WARNING]: [007]: [test_2]: }

    global DEBUG_MESSAGES

    if type(value) != str:
        value = json.dumps(value, indent=2)
    value = value.split('\n')
    if key:
        value = map(lambda v: '[%s]: %s' % (key, v), value)

    # We should add line numbers because Ansible removes the same warnings.
    # So, for example, some `}` characters from a JSON object will not be printed.
    last_line = len(DEBUG_MESSAGES) + 1
    value = map(lambda v: '[%03d%03d]: %s' % (RANDOM_PREFIX, last_line + v[0], v[1]), enumerate(value))

    DEBUG_MESSAGES += value


def warn(msg):
    global WARNINGS
    WARNINGS.append(msg)


def execute_module(argument_spec, function):
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = function(module.params)
    except Exception as e:
        res = ModuleRes(exception=e)
    res.exit(module)


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
    run_dir = run_dir if run_dir is not None else DEFAULT_RUN_DIR
    instance_fullname = get_instance_id(app_name, instance_name, stateboard)
    return os.path.join(run_dir, '%s.control' % instance_fullname)


def get_instance_pid_file(run_dir, app_name, instance_name=None, stateboard=False):
    run_dir = run_dir if run_dir is not None else DEFAULT_RUN_DIR
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


def get_cluster_instances(control_console):
    instances, _ = control_console.eval_res_err(GET_INSTANCES_FUNC_BODY)

    return instances


def get_cluster_instances_with_replicasets_info(control_console):
    instances, _ = control_console.eval_res_err(GET_INSTANCES_WITH_REPLICASETS_INFO_FUNC_BODY)

    return instances


def get_cluster_replicasets(control_console):
    cluster_replicasets, _ = control_console.eval_res_err(GET_REPLICASETS_FUNC_BODY)

    if not cluster_replicasets:
        cluster_replicasets = dict()

    return cluster_replicasets


def set_twophase_options(control_console, options):
    control_console.eval_res_err(SET_TWOPHASE_OPTIONS_FUNC_BODY, options)


def set_twophase_options_from_params(control_console, params):
    twophase_options = {}
    for name in TWOPHASE_OPTION_NAMES:
        if params.get(name) is not None:
            twophase_options[name] = params[name]

    set_twophase_options(control_console, twophase_options)


def read_yaml_file(control_console, file_path):
    return control_console.eval_res_err(READ_YAML_FILE_FUNC_BODY, file_path)


def get_clusterwide_config(control_console, filter_system=True):
    current_config, err = control_console.eval_res_err('''
        return require('cartridge').config_get_readonly()
    ''')
    if err is not None:
        return None, err
    if current_config is None:
        return None, "Cluster isn't bootstrapped yet"

    filtered = {}
    for key, value in current_config.items():
        if not key.endswith('.yml') and not (filter_system and key in SYSTEM_CONFIG_SECTIONS):
            filtered[key] = value
    return filtered, None


def patch_clusterwide_config(control_console, new_sections):
    current_config, err = get_clusterwide_config(control_console)
    if err is not None:
        return None, err

    patch = {}
    for section_name, section in new_sections.items():
        if section_name in SYSTEM_CONFIG_SECTIONS:
            return None, "Unable to patch config system section: '%s'" % section_name

        if current_config.get(section_name) != section:
            patch[section_name] = section

    if not patch:
        return False, None

    ok, err = control_console.eval_res_err('''
        return require('cartridge').config_patch_clusterwide(...)
    ''', patch)
    if not ok:
        return None, "Config patch failed: '%s'" % err

    return True, None


class Helpers:
    DYNAMIC_BOX_CFG_PARAMS = DYNAMIC_BOX_CFG_PARAMS
    MEMORY_SIZE_BOX_CFG_PARAMS = MEMORY_SIZE_BOX_CFG_PARAMS
    FORMAT_SERVER_FUNC = FORMAT_SERVER_FUNC
    FORMAT_REPLICASET_FUNC = FORMAT_REPLICASET_FUNC

    ModuleRes = ModuleRes
    CartridgeErrorCodes = CartridgeErrorCodes
    CartridgeException = CartridgeException
    Console = Console

    debug = staticmethod(debug)
    warn = staticmethod(warn)
    execute_module = staticmethod(execute_module)
    get_control_console = staticmethod(get_control_console)
    is_expelled = staticmethod(is_expelled)
    is_stateboard = staticmethod(is_stateboard)
    get_instance_id = staticmethod(get_instance_id)
    get_instance_console_sock = staticmethod(get_instance_console_sock)
    get_instance_pid_file = staticmethod(get_instance_pid_file)
    get_instance_dir = staticmethod(get_instance_dir)
    get_multiversion_instance_code_dir = staticmethod(get_multiversion_instance_code_dir)
    box_cfg_was_called = staticmethod(box_cfg_was_called)
    get_box_cfg = staticmethod(get_box_cfg)
    filter_none_values = staticmethod(filter_none_values)
    get_cluster_instances = staticmethod(get_cluster_instances)
    get_cluster_instances_with_replicasets_info = staticmethod(get_cluster_instances_with_replicasets_info)
    get_cluster_replicasets = staticmethod(get_cluster_replicasets)
    set_twophase_options = staticmethod(set_twophase_options)
    set_twophase_options_from_params = staticmethod(set_twophase_options_from_params)
    read_yaml_file = staticmethod(read_yaml_file)
    get_clusterwide_config = staticmethod(get_clusterwide_config)
    patch_clusterwide_config = staticmethod(patch_clusterwide_config)
