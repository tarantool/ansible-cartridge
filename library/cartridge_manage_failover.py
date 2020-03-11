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
        return require('cartridge').failover_get_params().enabled
    ''')

    if current_failover == failover:
        return ModuleRes(success=True, changed=False)

    enable = 'true' if failover else 'false'

    res = control_console.eval('''
        local failover, err = require('cartridge').failover_set_params({{enabled = {}}})
        return {{
            ok = failover ~= nil,
            err = err and err.err or require('json').NULL
        }}
    '''.format(enable))

    if not res['ok']:
        errmsg = 'Failed failover_set_params({{enabled={}}}): {}'.format(enable, res['err'])
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
