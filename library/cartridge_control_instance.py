#!/usr/bin/python

import requests

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes

argument_spec = {
    'hosts': {'required': True, 'type': 'list'},
    'hostvars': {'required': True, 'type': 'dict'}
}


def get_control_instance(params):
    meta = {
        'control_instance_address': None,
        'control_instance_port': None,
        'control_instance_host': None
    }

    control_instance = None
    control_host = None

    # Find leader of first replicaset
    host = params['hosts'][0]
    replicasets = params['hostvars'][host]['cartridge_replicasets']
    if replicasets:
        replicaset = replicasets[0]
        control_instance_name = replicaset['leader']

    # Get instance and host
    for host in params['hosts']:
        instances = params['hostvars'][host]['cartridge_instances']
        for i in instances:
            if i['name'] == control_instance_name:
                control_instance = i
                control_host = host
                break

    # If not found - get first instance
    if control_instance is None:
        for host in params['hosts']:
            instances = params['hostvars'][host]['cartridge_instances']

            if instances:
                control_instance = instances[0]
                control_host = host
                break

    if not control_instance:
        return ModuleRes(success=True, meta=meta)

    if 'ansible_host' in params['hostvars'][host]:
        meta['control_instance_address'] = params['hostvars'][control_host]['ansible_host']
    else:
        meta['control_instance_address'] = control_host

    meta['control_instance_port'] = control_instance['http_port']
    meta['control_instance_host'] = control_host

    return ModuleRes(success=True, meta=meta)

def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = get_control_instance(module.params)

    if res.success == True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
