#!/usr/bin/python

import os
import subprocess
import re

from ansible.module_utils.basic import AnsibleModule

from ansible.module_utils.helpers import ModuleRes


argument_spec = {
    'app_name': {'required': False, 'type': 'str'},
    'package_path': {'required': True, 'type': 'str'},
}


DEB = 'deb'
RPM = 'rpm'


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
    _, ext = os.path.splitext(package_path)
    if ext == '.rpm':
        return RPM
    elif ext == '.deb':
        return DEB
    raise Exception("Unknown package extension: %s" % ext)


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
        raise Exception("failed to get RPM deplist: %s" % output)

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
        raise Exception("failed to get DEB package info: %s" % output)

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
        'tnt_version': tnt_version
    }


def get_package_info(params):
    package_path = params['package_path']
    app_name = params.get('cartridge_app_name')

    package_type = get_package_type(package_path)

    if package_type == RPM:
        package_info = get_rpm_info(package_path)
    elif package_type == DEB:
        package_info = get_deb_info(package_path)
    else:
        raise Exception('Unknown package type: %s', package_type)

    if app_name and package_info['name'] != app_name:
        msg = 'cartridge_app_name value should be equal to package name. ' + \
              'Found cartridge_app_name: "%s", package name: "%s"' % (app_name, package_info['name'])
        return ModuleRes(success=False, msg=msg)

    package_info['package_type'] = package_type

    return ModuleRes(success=True, meta=package_info)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = get_package_info(module.params)
    except Exception as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
