#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console


argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
}


def bootstrap_vshard(params):
    control_console = get_control_console(params['console_sock'])
    can_bootstrap, _ = control_console.eval_res_err('''
        return require('cartridge.vshard-utils').can_bootstrap()
    ''')

    if not can_bootstrap:
        return ModuleRes(success=True, changed=False)

    ok, err = control_console.eval_res_err('''
        return require('cartridge.admin').bootstrap_vshard()
    ''')

    if not ok:
        errmsg = 'Vshard bootstrap failed: {}'.format(err)
        return ModuleRes(success=False, msg=errmsg)

    return ModuleRes(success=True, changed=True)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = bootstrap_vshard(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, **res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
