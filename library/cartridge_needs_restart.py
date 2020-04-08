#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException, cartridge_errcodes
from ansible.module_utils.helpers import get_control_console

import os


argument_spec = {
    'restart_forced': {'required': True, 'type': 'bool'},
    'control_sock': {'required': True, 'type': 'str'},
    'appname': {'required': True, 'type': 'str'},
    'instance_name': {'required': True, 'type': 'str'},
    'cluster_cookie': {'required': True, 'type': 'str'},
    'cartridge_defaults': {'required': True, 'type': 'dict'},
    'config': {'required': True, 'type': 'dict'},
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


def get_memtx_memory(control_console):
    return control_console.eval('''
        return type(box.cfg) ~= 'function' and box.cfg.memtx_memory or box.NULL
    ''')


def needs_restart(params):
    restart_forced = params['restart_forced']
    if restart_forced:
        return ModuleRes(success=True, changed=True)

    control_sock = params['control_sock']
    appname = params['appname']
    instance_name = params['instance_name']
    new_default_conf = params['cartridge_defaults']
    new_instance_conf = params['config']
    cluster_cookie = params['cluster_cookie']

    instance_conf_path = '/etc/tarantool/conf.d/{}.{}.yml'.format(appname, instance_name)
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
        instance_conf_path,
        control_console,
        '{}.{}'.format(appname, instance_name)
    )
    if check_conf_updated(new_instance_conf, current_instance_conf, ['memtx_memory']):
        return ModuleRes(success=True, changed=True)

    # check if default config was changed (except memtx_memory)
    current_default_conf = read_yaml_file_section(
        default_conf_path,
        control_console,
        appname
    )
    new_default_conf.update({'cluster_cookie': cluster_cookie})
    if check_conf_updated(new_default_conf, current_default_conf, ['memtx_memory']):
        return ModuleRes(success=True, changed=True)

    new_memtx_memory = None
    if 'memtx_memory' in new_instance_conf:
        new_memtx_memory = new_instance_conf['memtx_memory']
    elif 'memtx_memory' in new_default_conf:
        new_memtx_memory = new_default_conf['memtx_memory']

    # This code is ran after attempt to change memtx_memory in runtime
    # If current memtx_memory wasn't changed to the new value,
    # it mean that instance should be restarted to apply change
    if new_memtx_memory is not None:
        current_memtx_memory = get_memtx_memory(control_console)
        if current_memtx_memory != new_memtx_memory:
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
