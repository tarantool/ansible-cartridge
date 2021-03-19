#!/usr/bin/python

import os
import pkgutil

from ansible.module_utils.basic import AnsibleModule

if pkgutil.find_loader('ansible.module_utils.helpers'):
    import ansible.module_utils.helpers as helpers
else:
    import module_utils.helpers as helpers

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

    stateboard_name = helpers.get_instance_id(app_name, stateboard=True)
    systemd_units_info['stateboard_name'] = stateboard_name

    systemd_units_info['app_unit_file'] = '%s@.service' % app_name
    systemd_units_info['stateboard_unit_file'] = '%s.service' % stateboard_name

    systemd_units_info['instance_work_dir'] = helpers.get_instance_dir(
        instance_vars['cartridge_data_dir'], app_name, instance_name="%i"
    )
    systemd_units_info['stateboard_work_dir'] = helpers.get_instance_dir(
        instance_vars['cartridge_data_dir'], app_name, stateboard=True
    )

    systemd_units_info['instance_memtx_dir'] = None
    systemd_units_info['stateboard_memtx_dir'] = None
    if instance_vars['cartridge_memtx_dir_parent']:
        systemd_units_info['instance_memtx_dir'] = helpers.get_instance_dir(
            instance_vars['cartridge_memtx_dir_parent'], app_name, instance_name="%i"
        )
        systemd_units_info['stateboard_memtx_dir'] = helpers.get_instance_dir(
            instance_vars['cartridge_memtx_dir_parent'], app_name, stateboard=True
        )

    systemd_units_info['instance_vinyl_dir'] = None
    systemd_units_info['stateboard_vinyl_dir'] = None
    if instance_vars['cartridge_vinyl_dir_parent']:
        systemd_units_info['instance_vinyl_dir'] = helpers.get_instance_dir(
            instance_vars['cartridge_vinyl_dir_parent'], app_name, instance_name="%i"
        )
        systemd_units_info['stateboard_vinyl_dir'] = helpers.get_instance_dir(
            instance_vars['cartridge_vinyl_dir_parent'], app_name, stateboard=True
        )

    systemd_units_info['instance_wal_dir'] = None
    systemd_units_info['stateboard_wal_dir'] = None
    if instance_vars['cartridge_wal_dir_parent']:
        systemd_units_info['instance_wal_dir'] = helpers.get_instance_dir(
            instance_vars['cartridge_wal_dir_parent'], app_name, instance_name="%i"
        )
        systemd_units_info['stateboard_wal_dir'] = helpers.get_instance_dir(
            instance_vars['cartridge_wal_dir_parent'], app_name, stateboard=True
        )

    systemd_units_info['instance_pid_file'] = helpers.get_instance_pid_file(
        instance_vars['cartridge_run_dir'], app_name, instance_name="%i"
    )
    systemd_units_info['stateboard_pid_file'] = helpers.get_instance_pid_file(
        instance_vars['cartridge_run_dir'], app_name, stateboard=True
    )

    systemd_units_info['instance_console_sock'] = helpers.get_instance_console_sock(
        instance_vars['cartridge_run_dir'], app_name, instance_name="%i"
    )
    systemd_units_info['stateboard_console_sock'] = helpers.get_instance_console_sock(
        instance_vars['cartridge_run_dir'], app_name, stateboard=True
    )

    if not instance_vars['cartridge_multiversion']:
        instance_dist_dir = instance_vars['dist_dir']
        stateboard_dir = instance_vars['dist_dir']
    else:
        instances_dir = instance_vars['cartridge_app_instances_dir']

        instance_dist_dir = helpers.get_multiversion_instance_code_dir(
            instances_dir, app_name, instance_name="%i",
        )
        stateboard_dir = helpers.get_multiversion_instance_code_dir(
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

    return helpers.ModuleRes(changed=False, facts={
        'systemd_units_info': systemd_units_info
    })


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = get_systemd_units_info(module.params)
    except Exception as e:
        res = helpers.ModuleRes(exception=e)
    res.exit(module)


if __name__ == '__main__':
    main()
