#!/usr/bin/python

import os
import pwd
import grp
import yaml

from ansible.module_utils.basic import AnsibleModule


TARANTOOL_UID = pwd.getpwnam("tarantool").pw_uid
TARANTOOL_GID = grp.getgrnam("tarantool").gr_gid

class ModuleRes:
    def __init__(self, success, msg=None, changed=False):
        self.success = success
        self.msg = msg
        self.changed = changed


argument_spec = {
    'instance': {'required': True, 'type': 'dict'},
    'appname': {'required': True, 'type': 'str'},
    'config_defaults': {'required': True, 'type': 'dict'},
    'confdir': {'default': '/etc/tarantool/conf.d', 'type': 'str'}
}


def generate_config_files(params):
    if 'name' not in params['instance']:
        return ModuleRes(success=False, msg='Instance name must be specified')

    changed = False

    # Create default app config file if neccessary
    defaul_conf_name = '{}.yml'.format(params['appname'])
    defaul_conf_path = os.path.join(params['confdir'], defaul_conf_name)

    if not os.path.exists(defaul_conf_path):
        default_conf = params['config_defaults']
        if default_conf:
            default_conf = { params['appname'] : default_conf }
            with open(defaul_conf_path, 'w') as f:
                f.write(yaml.dump(default_conf, default_flow_style=False))
            os.chown(defaul_conf_path, TARANTOOL_UID, TARANTOOL_GID)

        changed = True

    # Create instance config file
    ## First - change config format
    deploy_params = ['name', 'roles', 'replica_for']
    section_name = '{}.{}'.format(params['appname'], params['instance']['name'])
    instance_conf = {
        section_name:
            {k: params['instance'][k]
                for k in params['instance'] if k not in deploy_params }
    }

    ## Dump in file
    conf_name = '{}.yml'.format(section_name)
    conf_path = os.path.join(params['confdir'], conf_name)

    if not os.path.exists(conf_path):
        with open(conf_path, 'w') as f:
            f.write(yaml.dump(instance_conf, default_flow_style=False))
        os.chown(conf_path, TARANTOOL_UID, TARANTOOL_GID)
        changed = True

    return ModuleRes(success=True, changed=changed)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = generate_config_files(module.params)

    if res.success == True:
        module.exit_json(changed=res.changed)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
