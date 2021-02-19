#!/usr/bin/python

import os
import pkgutil

if pkgutil.find_loader('ansible.module_utils.helpers'):
    import ansible.module_utils.helpers as helpers
else:
    import module_utils.helpers as helpers

argument_spec = {
    'app_name': {'required': False, 'type': 'str'},
    'instance_name': {'required': True, 'type': 'str'},
    'instance_vars': {'required': True, 'type': 'dict'},
}


def get_instance_pid_file(run_dir, app_name, instance_name, stateboard=False):
    instance_id = helpers.get_instance_id(app_name, instance_name, stateboard)
    return os.path.join(run_dir, '%s.pid' % instance_id)


def get_instance_conf_file(conf_dir, app_name, instance_name, stateboard=False):
    instance_id = helpers.get_instance_id(app_name, instance_name, stateboard)
    return os.path.join(conf_dir, '%s.yml' % instance_id)


def get_app_conf_file(conf_dir, app_name):
    return os.path.join(conf_dir, '%s.yml' % app_name)


def get_instance_conf_section(app_name, instance_name, stateboard=False):
    return helpers.get_instance_id(app_name, instance_name, stateboard)


def get_instance_work_dir(data_dir, app_name, instance_name, stateboard=False):
    instance_id = helpers.get_instance_id(app_name, instance_name, stateboard)
    return os.path.join(data_dir, instance_id)


def get_instance_systemd_service(app_name, instance_name, stateboard=False):
    if stateboard:
        return '%s-stateboard' % app_name
    return '%s@%s' % (app_name, instance_name)


def get_package_type(package_path):
    if package_path is None:
        return None
    if package_path.endswith('.rpm'):
        return 'rpm'
    if package_path.endswith('.deb'):
        return 'deb'
    if package_path.endswith('.tar.gz'):
        return 'tgz'

    raise Exception('Package of unsupported type is specified: %s' % package_path)


def get_instance_info(params):
    app_name = params['app_name']
    instance_name = params['instance_name']
    instance_vars = params['instance_vars']

    instance_info = {}

    package_path = instance_vars.get('cartridge_package_path')
    package_type = get_package_type(package_path)
    instance_info['package_type'] = package_type

    if package_type in ['rpm', 'deb']:
        instance_info['instance_code_dir'] = os.path.join(instance_vars['cartridge_dist_dir'], app_name)
    elif package_type is not None:
        return helpers.ModuleRes(failed=True, msg='Unknown package type: %s' % package_type)

    # app conf file, instance conf file, instance conf section
    instance_info['app_conf_file'] = get_app_conf_file(
        instance_vars['cartridge_conf_dir'], app_name
    )
    instance_info['conf_file'] = get_instance_conf_file(
        instance_vars['cartridge_conf_dir'], app_name, instance_name, instance_vars['stateboard'],
    )
    instance_info['conf_section'] = get_instance_conf_section(
        app_name, instance_name, instance_vars['stateboard']
    )

    # console socket, PID file paths
    instance_info['console_sock'] = helpers.get_instance_console_sock(
        instance_vars['cartridge_run_dir'], app_name, instance_name, instance_vars['stateboard']
    )

    instance_info['pid_file'] = get_instance_pid_file(
        instance_vars['cartridge_run_dir'], app_name, instance_name, instance_vars['stateboard']
    )

    # instance work dir
    instance_info['work_dir'] = get_instance_work_dir(
        instance_vars['cartridge_data_dir'], app_name, instance_name, instance_vars['stateboard']
    )

    # systemd service name
    instance_info['systemd_service'] = get_instance_systemd_service(
        app_name, instance_name, instance_vars['stateboard']
    )

    return helpers.ModuleRes(changed=False, facts={
        'instance_info': instance_info
    })


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_instance_info)
