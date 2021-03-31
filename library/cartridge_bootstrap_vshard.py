#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
}


def bootstrap_vshard(params):
    control_console = helpers.get_control_console(params['console_sock'])
    can_bootstrap, _ = control_console.eval_res_err('''
        return require('cartridge.vshard-utils').can_bootstrap()
    ''')

    if not can_bootstrap:
        return helpers.ModuleRes(changed=False)

    ok, err = control_console.eval_res_err('''
        return require('cartridge.admin').bootstrap_vshard()
    ''')

    if not ok:
        errmsg = 'Vshard bootstrap failed: {}'.format(err)
        return helpers.ModuleRes(failed=True, msg=errmsg)

    return helpers.ModuleRes()


if __name__ == '__main__':
    helpers.execute_module(argument_spec, bootstrap_vshard)
