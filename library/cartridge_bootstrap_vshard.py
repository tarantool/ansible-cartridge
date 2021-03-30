#!/usr/bin/python

from ansible.module_utils.helpers import execute_module, ModuleRes
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


if __name__ == '__main__':
    execute_module(argument_spec, bootstrap_vshard)
