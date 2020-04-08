#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console
from ansible.module_utils.helpers import instance_expelled


argument_spec = {
    'control_sock': {'required': True, 'type': 'str'},
    'hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
}


def probe_server(params):
    control_console = get_control_console(params['control_sock'])
    hostvars = params['hostvars']
    play_hosts = params['play_hosts']

    for i, instance_vars in hostvars.items():
        if 'config' not in instance_vars:
            continue

        if instance_expelled(instance_vars):
            continue

        res = control_console.eval('''
            local ok, err = require('cartridge').admin_probe_server('{}')
            return {{
                ok = ok and true or false,
                err = err and err.err or box.NULL
            }}
        '''.format(instance_vars['config']['advertise_uri']))

        if not res['ok'] and i in play_hosts:
            return ModuleRes(success=False, msg=res['err'])

    return ModuleRes(success=True)


def main():
    module = AnsibleModule(argument_spec=argument_spec)

    try:
        res = probe_server(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
