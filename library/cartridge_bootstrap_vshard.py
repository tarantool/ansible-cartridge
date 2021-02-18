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
        return ModuleRes(changed=False)

    ok, err = control_console.eval_res_err('''
        return require('cartridge.admin').bootstrap_vshard()
    ''')

    if not ok:
        errmsg = 'Vshard bootstrap failed: {}'.format(err)
        return ModuleRes(failed=True, msg=errmsg)

    return ModuleRes()


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = bootstrap_vshard(module.params)
    except CartridgeException as e:
        res = ModuleRes(exception=e)
    res.exit(module)


if __name__ == '__main__':
    main()
