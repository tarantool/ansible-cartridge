#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console


argument_spec = {
    'instance': {'required': True, 'type': 'dict'},
    'control_sock': {'required': True, 'type': 'str'},
}


def probe_server(params):
    control_console = get_control_console(params['control_sock'])
    res = control_console.eval('''
        local ok, err = require('cartridge').admin_probe_server('{}')
        return {{
            ok = ok and true or false,
            err = err and err.err or require('json').NULL
        }}
    '''.format(params['instance']['advertise_uri']))

    return ModuleRes(success=res['ok'], msg=res['err'])


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
