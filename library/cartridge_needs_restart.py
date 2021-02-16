#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException, cartridge_errcodes
from ansible.module_utils.helpers import get_control_console
from ansible.module_utils.helpers import dynamic_box_cfg_params
from ansible.module_utils.helpers import box_cfg_was_called
from ansible.module_utils.helpers import get_box_cfg

import os


argument_spec = {
    'app_name': {'required': True, 'type': 'str'},
    'config': {'required': True, 'type': 'dict'},
    'cartridge_defaults': {'required': True, 'type': 'dict'},
    'cluster_cookie': {'required': True, 'type': 'str'},
    'restarted': {'required': False, 'type': 'bool'},
    'stateboard': {'required': True, 'type': 'bool'},
    'instance_info': {'required': True, 'type': 'dict'},
}


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


def check_conf_updated(new_conf, old_conf, ignore_keys=[]):
    # check new conf keys
    for key, value in new_conf.items():
        if key not in ignore_keys:
            if key not in old_conf or old_conf[key] != value:
                return True

    # check old conf keys
    for key, value in old_conf.items():
        if key not in ignore_keys:
            if key not in new_conf or new_conf[key] != value:
                return True

    return False


def needs_restart(params):
    restarted = params['restarted']
    if restarted is True:
        return ModuleRes(success=True, changed=True)

    if restarted is False:
        return ModuleRes(success=True, changed=False)

    stateboard = params['stateboard']

    app_name = params['app_name']
    new_instance_conf = params['config']
    new_default_conf = params['cartridge_defaults']
    cluster_cookie = params['cluster_cookie']
    instance_info = params['instance_info']

    console_sock = instance_info['console_sock']

    # check if instance was not started yet
    if not os.path.exists(console_sock):
        return ModuleRes(success=True, changed=True)

    try:
        control_console = get_control_console(console_sock)
    except CartridgeException as e:
        allowed_errcodes = [
            cartridge_errcodes.SOCKET_NOT_FOUND,
            cartridge_errcodes.FAILED_TO_CONNECT_TO_SOCKET,
            cartridge_errcodes.INSTANCE_IS_NOT_STARTED_YET
        ]
        if e.code in allowed_errcodes:
            return ModuleRes(success=True, changed=True)

    last_restart_time = os.path.getmtime(console_sock)

    # check if application code was updated
    instance_code_dir = instance_info['instance_code_dir']
    package_update_time = os.path.getmtime(instance_code_dir)
    if last_restart_time < package_update_time:
        return ModuleRes(success=True, changed=True)

    # check if instance config was changed (except dynamic params)
    current_instance_conf, err = read_yaml_file_section(
        control_console,
        instance_info['conf_file'],
        instance_info['conf_section']
    )
    if err is not None:
        return ModuleRes(success=False, msg="Failed to read current instance config: %s" % err)

    if check_conf_updated(new_instance_conf, current_instance_conf, dynamic_box_cfg_params):
        return ModuleRes(success=True, changed=True)

    if not stateboard:
        # check if default config was changed (except dynamic params)
        current_default_conf, err = read_yaml_file_section(
            control_console,
            instance_info['app_conf_file'],
            app_name
        )
        if err is not None:
            return ModuleRes(success=False, msg="Failed to read current default config: %s" % err)

        new_default_conf.update({'cluster_cookie': cluster_cookie})
        if check_conf_updated(new_default_conf, current_default_conf, dynamic_box_cfg_params):
            return ModuleRes(success=True, changed=True)

    # if box.cfg wasn't called,
    if not box_cfg_was_called(control_console):
        return ModuleRes(success=True, changed=True)

    current_cfg = get_box_cfg(control_console)
    if current_cfg is None:
        return ModuleRes(success=True, changed=True)

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
                return ModuleRes(success=True, changed=True)

    return ModuleRes(success=True, changed=False)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = needs_restart(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, **res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
