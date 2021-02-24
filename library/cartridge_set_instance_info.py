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


def get_instance_conf_file(conf_dir, app_name, instance_name, stateboard=False):
    instance_id = helpers.get_instance_id(app_name, instance_name, stateboard)
    return os.path.join(conf_dir, '%s.yml' % instance_id)


def get_app_conf_file(conf_dir, app_name):
    return os.path.join(conf_dir, '%s.yml' % app_name)


def get_instance_conf_section(app_name, instance_name, stateboard=False):
    return helpers.get_instance_id(app_name, instance_name, stateboard)


def get_instance_systemd_service(app_name, instance_name, stateboard=False):
    if stateboard:
        return '%s-stateboard' % app_name
    return '%s@%s' % (app_name, instance_name)


def get_multiversion_app_code_dir(install_dir, package_path):
    package_basename = os.path.basename(package_path)

    # get name and version
    package_name_version, ext = os.path.splitext(package_basename)
    if ext == '.gz' and package_name_version.endswith('.tar'):
        package_name_version, _ = os.path.splitext(package_name_version)

    app_dir = os.path.join(install_dir, package_name_version)
    return app_dir


def get_multiversion_instance_code_dir(instances_dir, app_name, instance_name=None, stateboard=False):
    instance_id = helpers.get_instance_id(app_name, instance_name, stateboard)
    return os.path.join(instances_dir, instance_id)


def get_bin_dirs_info(app_name, instance_name, instance_vars):
    bin_dirs_info = {}

    if not instance_vars['cartridge_multiversion']:
        app_dir = os.path.join(instance_vars['cartridge_install_dir'], app_name)

        bin_dirs_info['app_dir'] = app_dir
        bin_dirs_info['instance_dir'] = app_dir
        bin_dirs_info['systemd_instance_code_dir'] = app_dir
        bin_dirs_info['systemd_stateboard_code_dir'] = app_dir
    else:
        bin_dirs_info['app_dir'] = get_multiversion_app_code_dir(
            instance_vars['cartridge_install_dir'],
            instance_vars['cartridge_package_path']
        )

        instances_dir = instance_vars['cartridge_instances_dir']

        bin_dirs_info['instance_dir'] = get_multiversion_instance_code_dir(
            instances_dir, app_name, instance_name, instance_vars['stateboard'],
        )

        bin_dirs_info['systemd_instance_code_dir'] = get_multiversion_instance_code_dir(
            instances_dir, app_name, instance_name="%i",
        )
        bin_dirs_info['systemd_stateboard_code_dir'] = get_multiversion_instance_code_dir(
            instances_dir, app_name, stateboard=True,
        )

    return bin_dirs_info


def get_instance_info(params):
    app_name = params['app_name']
    instance_name = params['instance_name']
    instance_vars = params['instance_vars']

    instance_info = {}

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

    instance_info['pid_file'] = helpers.get_instance_pid_file(
        instance_vars['cartridge_run_dir'], app_name, instance_name, instance_vars['stateboard']
    )

    # instance work dir
    instance_info['work_dir'] = helpers.get_instance_work_dir(
        instance_vars['cartridge_data_dir'], app_name, instance_name, instance_vars['stateboard']
    )

    # systemd service name
    instance_info['systemd_service'] = get_instance_systemd_service(
        app_name, instance_name, instance_vars['stateboard']
    )

    # tmpfiles conf
    instance_info['tmpfiles_conf'] = os.path.join(
        instance_vars['cartridge_tmpfiles_dir'], '%s.conf' % app_name
    )

    # code dirs
    bin_dirs_info = get_bin_dirs_info(app_name, instance_name, instance_vars)
    instance_info.update(bin_dirs_info)

    return helpers.ModuleRes(changed=False, facts={
        'instance_info': instance_info
    })


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_instance_info)
