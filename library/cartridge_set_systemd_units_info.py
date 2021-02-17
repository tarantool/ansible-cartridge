#!/usr/bin/python

import os

from ansible.module_utils.basic import AnsibleModule

from ansible.module_utils.helpers import ModuleRes
from ansible.module_utils.helpers import get_instance_id
from ansible.module_utils.helpers import get_instance_console_sock
from ansible.module_utils.helpers import get_instance_pid_file
from ansible.module_utils.helpers import get_instance_work_dir


argument_spec = {
    'app_name': {'required': False, 'type': 'str'},
    'instance_vars': {'required': True, 'type': 'dict'},
    'tnt_version': {'required': False, 'type': 'str'},
}


def get_systemd_units_info(params):
    app_name = params['app_name']
    instance_vars = params['instance_vars']
    tnt_version = params['tnt_version']

    systemd_units_info = {}

    stateboard_name = get_instance_id(app_name, None, stateboard=True)
    systemd_units_info['stateboard_name'] = stateboard_name

    systemd_units_info['app_unit_file'] = '%s@.service' % app_name
    systemd_units_info['stateboard_unit_file'] = '%s.service' % stateboard_name

    systemd_units_info['instance_work_dir'] = get_instance_work_dir(
        instance_vars['cartridge_data_dir'], app_name, "%i"
    )
    systemd_units_info['stateboard_work_dir'] = get_instance_work_dir(
        instance_vars['cartridge_data_dir'], app_name, None, stateboard=True
    )

    systemd_units_info['instance_pid_file'] = get_instance_pid_file(
        instance_vars['cartridge_run_dir'], app_name, "%i"
    )
    systemd_units_info['stateboard_pid_file'] = get_instance_pid_file(
        instance_vars['cartridge_run_dir'], app_name, None, stateboard=True
    )

    systemd_units_info['instance_console_sock'] = get_instance_console_sock(
        instance_vars['cartridge_run_dir'], app_name, "%i"
    )
    systemd_units_info['stateboard_console_sock'] = get_instance_console_sock(
        instance_vars['cartridge_run_dir'], app_name, None, stateboard=True
    )

    instance_code_dir = instance_vars['systemd_instance_code_dir']
    stateboard_code_dir = instance_vars['systemd_stateboard_code_dir']

    systemd_units_info['instance_entrypoint'] = os.path.join(instance_code_dir, 'init.lua')
    systemd_units_info['stateboard_entrypoint'] = os.path.join(stateboard_code_dir, 'stateboard.init.lua')

    if tnt_version:
        opensource_tarantool_binary = '/usr/bin/tarantool'
        systemd_units_info['instance_tarantool_binary'] = opensource_tarantool_binary
        systemd_units_info['stateboard_tarantool_binary'] = opensource_tarantool_binary
    else:
        systemd_units_info['instance_tarantool_binary'] = os.path.join(instance_code_dir, 'tarantool')
        systemd_units_info['stateboard_tarantool_binary'] = os.path.join(stateboard_code_dir, 'tarantool')

    return ModuleRes(changed=False, facts={
        'systemd_units_info': systemd_units_info
    })


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = get_systemd_units_info(module.params)
    except Exception as e:
        res = ModuleRes(exception=e)
    res.exit(module)


if __name__ == '__main__':
    main()
