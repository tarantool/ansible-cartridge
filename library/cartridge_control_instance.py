#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console

argument_spec = {
    'sock': {'requires': True, 'type': 'str'},
    'allow_empty': {'requires': True, 'type': 'bool', 'default': True}
}


def get_control_instance(params):
    control_console = get_control_console(params['sock'])
    control_instance = ''

    members = control_console.eval('''
        return require('membership').members()
    ''')

    for _, member in members.items():
        if 'payload' in member and member['payload'].get('uuid') is not None:
            if member['payload'].get('alias') is None:
                errmsg = 'Unable to get instance alias for "{}"'.format(member['payload']['uuid'])
                return ModuleRes(success=False, msg=errmsg)

            control_instance = member['payload']['alias']
            break

    if not control_instance and not params['allow_empty']:
        errmsg = "Cluster isn't bootstrapped yet"
        return ModuleRes(success=False, msg=errmsg)

    return ModuleRes(success=True, meta={'host': control_instance})


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = get_control_instance(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
