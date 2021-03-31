#!/usr/bin/env python

import os
import re
import subprocess
import tarfile

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'app_name': {'required': True, 'type': 'str'},
    'package_path': {'required': True, 'type': 'str'},
}


def run_command_and_get_output(cmd):
    process = subprocess.Popen(
        cmd,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE
    )

    stdout, _ = process.communicate()
    stdout = stdout.decode('utf-8')

    return process.returncode, stdout


def get_package_type(package_path):
    if package_path.endswith('.rpm'):
        return 'rpm'
    if package_path.endswith('.deb'):
        return 'deb'
    if package_path.endswith('.tar.gz'):
        return 'tgz'

    raise Exception('Package of unsupported type is specified: %s' % package_path)


def get_rpm_info(package_path):
    # package name
    cmd = ['rpm', '-qip', package_path]
    rc, output = run_command_and_get_output(cmd)
    if rc != 0:
        raise Exception("failed to get RPM package info: %s" % output)

    m = re.search(r'Name\s*:\s*([^\n]+)\n', output)
    if m is None:
        raise Exception("Failed to find package name in package info: %s" % output)

    package_name = m.groups()[0]
    # Tarantool dependency
    tnt_version = None

    cmd = ['rpm', '-qpR', package_path]
    rc, output = run_command_and_get_output(cmd)
    if rc != 0:
        raise Exception("Failed to get RPM deplist: %s" % output)

    m = re.search(r'tarantool >= ([0-9]+.[0-9]+)', output)
    if m is not None:
        tnt_version = m.groups()[0]

    return {
        'name': package_name,
        'tnt_version': tnt_version,
    }


def get_deb_info(package_path):
    cmd = ['dpkg', '-I', package_path]
    rc, output = run_command_and_get_output(cmd)
    if rc != 0:
        raise Exception("Failed to get DEB package info: %s" % output)

    # package name
    m = re.search(r'Package\s*:\s*([^\n]+)\n', output)
    if m is None:
        raise Exception("Failed to find package name in package info: %s" % output)

    package_name = m.groups()[0]

    # Tarantool dependency
    tnt_version = None

    m = re.search(r'Depends\s*:\s*([^\n]+)\n', output)
    if m is not None:
        deplist = m.groups()[0]
        m = re.search(r'tarantool\s+\(\s*>=\s*([0-9]+.[0-9]+)', deplist)
        if m is not None:
            tnt_version = m.groups()[0]

    return {
        'name': package_name,
        'tnt_version': tnt_version,
    }


def get_tgz_info(package_path, app_name):
    tnt_version = None

    with tarfile.open(package_path) as tar:
        names = tar.getnames()
        if app_name not in names:
            raise Exception("Package should contain '%s' directory" % app_name)

        tarantool_binary_path = os.path.join(app_name, 'tarantool')
        tnt_is_enterprise = tarantool_binary_path in names

        if not tnt_is_enterprise:
            version_file_path = os.path.join(app_name, 'VERSION')
            try:
                member = tar.getmember(version_file_path)
            except KeyError:
                raise Exception("Package should contain %s file" % version_file_path)

            version_file = tar.extractfile(member)
            version_file_lines = version_file.readlines()

            for line in version_file_lines:
                m = re.search(r'TARANTOOL=(\d+\.\d+)\.', line.decode())
                if m is not None:
                    tnt_version = m.groups()[0]
                    break

    return {
        'name': app_name,
        'tnt_version': tnt_version,
    }


def get_package_info(params):
    package_path = params['package_path']
    app_name = params['app_name']

    package_type = get_package_type(package_path)

    if package_type == 'rpm':
        package_info = get_rpm_info(package_path)
    elif package_type == 'deb':
        package_info = get_deb_info(package_path)
    elif package_type == 'tgz':
        package_info = get_tgz_info(package_path, app_name)
    else:
        return helpers.ModuleRes(failed=True, msg='Unknown package type: %s' % package_type)

    if app_name and package_info['name'] != app_name:
        msg = 'cartridge_app_name value should be equal to package name. ' + \
              'Found cartridge_app_name: "%s", package name: "%s"' % (app_name, package_info['name'])
        return helpers.ModuleRes(failed=True, msg=msg)

    package_info['type'] = package_type

    return helpers.ModuleRes(changed=False, fact=package_info)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_package_info)
