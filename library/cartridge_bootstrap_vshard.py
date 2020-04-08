#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console


argument_spec = {
    'control_sock': {'required': True, 'type': 'str'},
}


def bootstrap_vshard(params):
    control_console = get_control_console(params['control_sock'])
    can_bootstrap = control_console.eval('''
        return require('cartridge.vshard-utils').can_bootstrap()
    ''')

    if not can_bootstrap:
        return ModuleRes(success=True, changed=False)

    res = control_console.eval('''
        local ok, err = require('cartridge.admin').bootstrap_vshard()
        return {
            ok = ok or box.NULL,
            err = err and err.err or box.NULL
        }
    ''')

    if not res['ok']:
        errmsg = 'Bootstrap vshard failed: {}'.format(res['err'])
        return ModuleRes(success=False, msg=errmsg)

    return ModuleRes(success=True, changed=True)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = bootstrap_vshard(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
