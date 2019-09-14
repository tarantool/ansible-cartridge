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
    }

    for host in params['hosts']:
        instances = params['hostvars'][host]['cartridge_config']['instances']
        if len(instances) > 0:
            control_instance = instances[0]
            if 'ansible_host' in params['hostvars'][host]:
                meta['control_instance_address'] = params['hostvars'][host]['ansible_host']
            else:
                meta['control_instance_address'] = host
            meta['control_instance_port'] = control_instance['http_port']

            break

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
