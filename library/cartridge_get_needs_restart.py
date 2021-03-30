#!/usr/bin/python

import os

from ansible.module_utils.helpers import execute_module, ModuleRes
from ansible.module_utils.helpers import get_control_console
from ansible.module_utils.helpers import dynamic_box_cfg_params
from ansible.module_utils.helpers import get_box_cfg, box_cfg_was_called
from ansible.module_utils.helpers import CartridgeException, cartridge_errcodes

argument_spec = {
    'check_package_updated': {'required': False, 'type': 'bool', 'default': False},
    'check_config_updated': {'required': False, 'type': 'bool', 'default': False},

    'instance_info': {'required': True, 'type': 'dict'},
    'app_name': {'required': False, 'type': 'str'},
    'config': {'required': False, 'type': 'dict'},
    'cartridge_defaults': {'required': False, 'type': 'dict'},
    'cluster_cookie': {'required': False, 'type': 'str'},
    'stateboard': {'required': False, 'type': 'bool'},
}


def check_needs_restart_to_update_package(params):
    instance_info = params['instance_info']
    console_sock = instance_info['console_sock']
    instance_dist_dir = instance_info['instance_dist_dir']

    last_restart_time = os.path.getmtime(console_sock)

    # check if application code was updated
    package_update_time = os.path.getmtime(instance_dist_dir)
    if last_restart_time < package_update_time:
        return True, None

    return False, None


def read_yaml_file_section(control_console, filepath, section):
    func_body = '''
        local filepath = ...
        local file = require('fio').open(filepath)
        if file == nil then
            return nil, 'Failed to open instance config file'
        end

        local buf = {}
        while true do
            local val = file:read(1024)
            if val == nil then
                error('Failed to read from instance config file')
            elseif val == '' then
                break
            end
            table.insert(buf, val)
        end
        file:close()

        local data = table.concat(buf, '')
        local ok, ret = pcall(require('yaml').decode, data)
        if not ok then
            return nil, 'Failed to decode instance config from YAML'
        end
        return ret
    '''

    sections, err = control_console.eval_res_err(func_body, filepath)
    if err is not None:
        return None, err

    if section not in sections:
        return None, 'File {} does not contain section: {}'.format(filepath, section)

    return sections[section], None


def check_conf_updated(new_conf, old_conf, ignore_keys):
    # check new conf keys
    for key, value in new_conf.items():
        if key not in ignore_keys or []:
            if key not in old_conf or old_conf[key] != value:
                return True

    # check old conf keys
    for key, value in old_conf.items():
        if key not in ignore_keys or []:
            if key not in new_conf or new_conf[key] != value:
                return True

    return False


def check_needs_restart_to_update_config(params, control_console):
    required_args = {
        'app_name',
        'config',
        'cartridge_defaults',
        'cluster_cookie',
        'stateboard',
    }
    for arg in required_args:
        if params.get(arg) is None:
            return None, "Argument '%s' is required to check for configuration updates" % arg

    instance_info = params['instance_info']
    app_name = params['app_name']
    new_instance_conf = params['config']
    new_default_conf = params['cartridge_defaults']
    cluster_cookie = params['cluster_cookie']
    stateboard = params['stateboard']

    if not os.path.exists(instance_info['conf_file']):
        return True, None

    # check if instance config was changed (except dynamic params)
    current_instance_conf, err = read_yaml_file_section(
        control_console,
        instance_info['conf_file'],
        instance_info['instance_id']
    )
    if err is not None:
        return None, "Failed to read current instance config: %s" % err

    if check_conf_updated(new_instance_conf, current_instance_conf, dynamic_box_cfg_params):
        return True, None

    if not stateboard:
        if not os.path.exists(instance_info['app_conf_file']):
            return True, None

        # check if default config was changed (except dynamic params)
        current_default_conf, err = read_yaml_file_section(
            control_console,
            instance_info['app_conf_file'],
            app_name
        )
        if err is not None:
            return None, "Failed to read current default config: %s" % err

        new_default_conf.update({'cluster_cookie': cluster_cookie})
        if check_conf_updated(new_default_conf, current_default_conf, dynamic_box_cfg_params):
            return True, None

    # if box.cfg wasn't called,
    if not box_cfg_was_called(control_console):
        return True, None

    current_cfg = get_box_cfg(control_console)
    if current_cfg is None:
        return True, None

    for param_name in dynamic_box_cfg_params:
        new_value = None
        if param_name in new_instance_conf:
            new_value = new_instance_conf[param_name]
        elif not stateboard and param_name in new_default_conf:
            new_value = new_default_conf[param_name]

        # This code is ran after attempt to change parameter in runtime
        # If current parameter wasn't changed to the new value,
        # it mean that instance should be restarted to apply change
        if new_value is not None:
            if current_cfg.get(param_name) != new_value:
                return True, None

    return False, None


def set_needs_restart(params):
    instance_info = params['instance_info']
    console_sock = instance_info['console_sock']

    # check if instance was not started yet
    if not os.path.exists(console_sock):
        return ModuleRes(changed=True, fact=True)

    try:
        control_console = get_control_console(console_sock)
    except CartridgeException as e:
        allowed_errcodes = [
            cartridge_errcodes.SOCKET_NOT_FOUND,
            cartridge_errcodes.FAILED_TO_CONNECT_TO_SOCKET,
            cartridge_errcodes.INSTANCE_IS_NOT_STARTED_YET
        ]
        if e.code in allowed_errcodes:
            return ModuleRes(changed=True, fact=True)

        raise e

    if params['check_package_updated']:
        needs_restart, err = check_needs_restart_to_update_package(params)
        if err is not None:
            return ModuleRes(failed=True, msg=err)
        if needs_restart:
            return ModuleRes(changed=True, fact=True)

    if params['check_config_updated']:
        needs_restart, err = check_needs_restart_to_update_config(params, control_console)
        if err is not None:
            return ModuleRes(failed=True, msg=err)
        if needs_restart:
            return ModuleRes(changed=True, fact=True)

    return ModuleRes(changed=False, fact=False)


if __name__ == '__main__':
    execute_module(argument_spec, set_needs_restart)
