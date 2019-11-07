#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes

argument_spec = {
    'hosts': {'required': True, 'type': 'list'},
    'hostvars': {'required': True, 'type': 'dict'},
    'appname': {'requires': True, 'type': 'str'},
}


def get_control_instance(params):
    meta = {
        'control_sock': None,
        'control_host': None
    }

    control_host = params['hosts'][0]
    meta['control_host'] = control_host
    meta['control_sock'] = '/var/run/tarantool/{}.{}.control'.format(params['appname'], control_host)

    return ModuleRes(success=True, meta=meta)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = get_control_instance(module.params)

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
