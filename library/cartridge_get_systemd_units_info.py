#!/usr/bin/python

import os

from ansible.module_utils.helpers import execute_module, ModuleRes
from ansible.module_utils.helpers import get_instance_id
from ansible.module_utils.helpers import get_instance_pid_file
from ansible.module_utils.helpers import get_instance_console_sock
from ansible.module_utils.helpers import get_instance_dir
from ansible.module_utils.helpers import get_multiversion_instance_code_dir

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

    stateboard_name = get_instance_id(app_name, stateboard=True)
    systemd_units_info['stateboard_name'] = stateboard_name

    systemd_units_info['app_unit_file'] = '%s@.service' % app_name
    systemd_units_info['stateboard_unit_file'] = '%s.service' % stateboard_name

    systemd_units_info['instance_work_dir'] = get_instance_dir(
        instance_vars['cartridge_data_dir'], app_name, instance_name="%i"
    )
    systemd_units_info['stateboard_work_dir'] = get_instance_dir(
        instance_vars['cartridge_data_dir'], app_name, stateboard=True
    )

    systemd_units_info['instance_memtx_dir'] = None
    systemd_units_info['stateboard_memtx_dir'] = None
    if instance_vars['cartridge_memtx_dir_parent']:
        systemd_units_info['instance_memtx_dir'] = get_instance_dir(
            instance_vars['cartridge_memtx_dir_parent'], app_name, instance_name="%i"
        )
        systemd_units_info['stateboard_memtx_dir'] = get_instance_dir(
            instance_vars['cartridge_memtx_dir_parent'], app_name, stateboard=True
        )

    systemd_units_info['instance_vinyl_dir'] = None
    systemd_units_info['stateboard_vinyl_dir'] = None
    if instance_vars['cartridge_vinyl_dir_parent']:
        systemd_units_info['instance_vinyl_dir'] = get_instance_dir(
            instance_vars['cartridge_vinyl_dir_parent'], app_name, instance_name="%i"
        )
        systemd_units_info['stateboard_vinyl_dir'] = get_instance_dir(
            instance_vars['cartridge_vinyl_dir_parent'], app_name, stateboard=True
        )

    systemd_units_info['instance_wal_dir'] = None
    systemd_units_info['stateboard_wal_dir'] = None
    if instance_vars['cartridge_wal_dir_parent']:
        systemd_units_info['instance_wal_dir'] = get_instance_dir(
            instance_vars['cartridge_wal_dir_parent'], app_name, instance_name="%i"
        )
        systemd_units_info['stateboard_wal_dir'] = get_instance_dir(
            instance_vars['cartridge_wal_dir_parent'], app_name, stateboard=True
        )

    systemd_units_info['instance_pid_file'] = get_instance_pid_file(
        instance_vars['cartridge_run_dir'], app_name, instance_name="%i"
    )
    systemd_units_info['stateboard_pid_file'] = get_instance_pid_file(
        instance_vars['cartridge_run_dir'], app_name, stateboard=True
    )

    systemd_units_info['instance_console_sock'] = get_instance_console_sock(
        instance_vars['cartridge_run_dir'], app_name, instance_name="%i"
    )
    systemd_units_info['stateboard_console_sock'] = get_instance_console_sock(
        instance_vars['cartridge_run_dir'], app_name, stateboard=True
    )

    if not instance_vars['cartridge_multiversion']:
        instance_dist_dir = instance_vars['dist_dir']
        stateboard_dir = instance_vars['dist_dir']
    else:
        instances_dir = instance_vars['cartridge_app_instances_dir']

        instance_dist_dir = get_multiversion_instance_code_dir(
            instances_dir, app_name, instance_name="%i",
        )
        stateboard_dir = get_multiversion_instance_code_dir(
            instances_dir, app_name, stateboard=True,
        )

    systemd_units_info['instance_entrypoint'] = os.path.join(instance_dist_dir, 'init.lua')
    systemd_units_info['stateboard_entrypoint'] = os.path.join(stateboard_dir, 'stateboard.init.lua')

    if tnt_version:
        opensource_tarantool_binary = '/usr/bin/tarantool'
        systemd_units_info['instance_tarantool_binary'] = opensource_tarantool_binary
        systemd_units_info['stateboard_tarantool_binary'] = opensource_tarantool_binary
    else:
        systemd_units_info['instance_tarantool_binary'] = os.path.join(instance_dist_dir, 'tarantool')
        systemd_units_info['stateboard_tarantool_binary'] = os.path.join(stateboard_dir, 'tarantool')

    return ModuleRes(changed=False, fact=systemd_units_info)


if __name__ == '__main__':
    execute_module(argument_spec, get_systemd_units_info)
