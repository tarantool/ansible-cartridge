#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes

argument_spec = {
    'hostvars': {'required': True, 'type': 'dict'},
    'appname': {'requires': True, 'type': 'str'},
}


def get_control_instance(params):
    hostvars = params['hostvars']
    appname = params['appname']

    control_instance = None
    control_sock = None

    for i, instance_vars in hostvars.items():
        if 'joined' in instance_vars and instance_vars['joined']:
            control_instance = i
            control_sock = '/var/run/tarantool/{}.{}.control'.format(appname, control_instance)
            break

    if control_instance is None:
        errmsg = 'Unable to run cartridge config tasks - cluster is not bootstrapped yet. ' + \
            'Skip `cartridge-control` tag or do not specify cartridge config variables'
        return ModuleRes(success=False, msg=errmsg)

    return ModuleRes(success=True, meta={
        'control_instance': control_instance,
        'control_sock': control_sock,
    })


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = get_control_instance(module.params)

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
