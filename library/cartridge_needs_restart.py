#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException, cartridge_errcodes
from ansible.module_utils.helpers import get_control_console
from ansible.module_utils.helpers import dynamic_box_cfg_params

import os


argument_spec = {
    'restarted': {'required': False, 'type': 'bool'},
    'control_sock': {'required': True, 'type': 'str'},
    'appname': {'required': True, 'type': 'str'},
    'instance_conf_file': {'required': True, 'type': 'str'},
    'conf_section_name': {'required': True, 'type': 'str'},
    'cluster_cookie': {'required': True, 'type': 'str'},
    'cartridge_defaults': {'required': True, 'type': 'dict'},
    'config': {'required': True, 'type': 'dict'},
    'stateboard': {'required': True, 'type': 'bool'}
}


def read_yaml_file_section(filepath, control_console, section):
    sections = control_console.eval('''
        local file = require('fio').open('{}')
        if file == nil then
            error('Failed to open instance config file')
        end

        local buf = {{}}
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
            error('Failed to decode instance config from YAML')
        end
        return ret
    '''.format(filepath))

    if section not in sections:
        errmsg = 'File {} does not contain section: {}'.format(filepath, section)
        raise CartridgeException(cartridge_errcodes.MISSED_SECTION, errmsg)

    return sections[section]


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


def get_current_cfg(control_console):
    return control_console.eval('''
        return type(box.cfg) ~= 'function' and box.cfg or box.NULL
    ''')


def needs_restart(params):
    restarted = params['restarted']
    if restarted is True:
        return ModuleRes(success=True, changed=True)

    if restarted is False:
        return ModuleRes(success=True, changed=False)

    stateboard = params['stateboard']

    control_sock = params['control_sock']
    appname = params['appname']
    new_default_conf = params['cartridge_defaults']
    new_instance_conf = params['config']
    cluster_cookie = params['cluster_cookie']
    instance_conf_file = params['instance_conf_file']
    conf_section_name = params['conf_section_name']

    default_conf_path = '/etc/tarantool/conf.d/{}.yml'.format(appname)
    app_code_path = '/usr/share/tarantool/{}'.format(appname)

    # check if instance was not started yet
    if not os.path.exists(control_sock):
        return ModuleRes(success=True, changed=True)

    try:
        control_console = get_control_console(control_sock)
    except CartridgeException as e:
        allowed_errcodes = [
            cartridge_errcodes.SOCKET_NOT_FOUND,
            cartridge_errcodes.FAILED_TO_CONNECT_TO_SOCKET,
            cartridge_errcodes.INSTANCE_IS_NOT_STARTED_YET
        ]
        if e.code in allowed_errcodes:
            return ModuleRes(success=True, changed=True)

    last_restart_time = os.path.getmtime(control_sock)

    # check if application code was updated
    package_update_time = os.path.getmtime(app_code_path)
    if last_restart_time < package_update_time:
        return ModuleRes(success=True, changed=True)

    # check if instance config was changed (except memtx_memory)
    current_instance_conf = read_yaml_file_section(
        instance_conf_file,
        control_console,
        conf_section_name
    )
    if check_conf_updated(new_instance_conf, current_instance_conf, dynamic_box_cfg_params):
        return ModuleRes(success=True, changed=True)

    if not stateboard:
        # check if default config was changed (except memtx_memory)
        current_default_conf = read_yaml_file_section(
            default_conf_path,
            control_console,
            appname
        )
        new_default_conf.update({'cluster_cookie': cluster_cookie})
        if check_conf_updated(new_default_conf, current_default_conf, dynamic_box_cfg_params):
            return ModuleRes(success=True, changed=True)

    current_cfg = get_current_cfg(control_console)

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
            if current_cfg[param_name] != new_value:
                return ModuleRes(success=True, changed=True)

    return ModuleRes(success=True, changed=False)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = needs_restart(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
