#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'netbox_call_timeout': {'required': False, 'type': 'int'},
    'upload_config_timeout': {'required': False, 'type': 'int'},
    'apply_config_timeout': {'required': False, 'type': 'int'},
    'validate_config_timeout': {'required': False, 'type': 'int'},
}


def bootstrap_vshard(params):
    control_console = helpers.get_control_console(params['console_sock'])

    helpers.set_twophase_options_from_params(control_console, params)

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
