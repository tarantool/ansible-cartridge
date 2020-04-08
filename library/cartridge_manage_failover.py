#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console


argument_spec = {
    'control_sock': {'required': True, 'type': 'str'},
    'failover': {'required': True, 'type': 'bool'},
}


def manage_failover(params):
    failover = params['failover']
    control_console = get_control_console(params['control_sock'])

    current_failover = control_console.eval('''
        return require('cartridge').admin_get_failover()
    ''')

    if current_failover == failover:
        return ModuleRes(success=True, changed=False)

    function_name = 'admin_enable_failover' if failover else 'admin_disable_failover'

    res = control_console.eval('''
        local failover, err = require('cartridge').{}()
        return {{
            ok = failover ~= nil,
            err = err and err.err or box.NULL
        }}
    '''.format(function_name))

    if not res['ok']:
        errmsg = 'Failed {}: {}'.format(function_name, res['err'])
        return ModuleRes(success=False, msg=errmsg)

    return ModuleRes(success=True, changed=True)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = manage_failover(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
