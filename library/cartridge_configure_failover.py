#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'failover_params': {'required': False, 'type': 'raw'},
    'netbox_call_timeout': {'required': False, 'type': 'int'},
    'upload_config_timeout': {'required': False, 'type': 'int'},
    'apply_config_timeout': {'required': False, 'type': 'int'},
}

NEW_FAILOVER_API_CARTRIDGE_VERSION = '2.1.0'
DEFAULT_STATE_PROVIDER = 'tarantool'


def get_tarantool_version(control_console):
    version, _ = control_console.eval_res_err('''
        return require('cartridge').VERSION
    ''')
    return version


def manage_failover_old(control_console, failover_params):
    failover_enabled = failover_params['mode'] == 'eventual'

    current_failover, _ = control_console.eval_res_err('''
        return require('cartridge').admin_get_failover()
    ''')

    if current_failover == failover_enabled:
        return helpers.ModuleRes(changed=False)

    function_name = 'admin_enable_failover' if failover_enabled else 'admin_disable_failover'

    func_body = '''
        local function_name = ...
        return require('cartridge')[function_name]()
    '''
    _, err = control_console.eval_res_err(func_body, function_name)

    if err is not None:
        errmsg = 'Failed {}: {}'.format(function_name, err)
        return helpers.ModuleRes(failed=True, msg=errmsg)

    return helpers.ModuleRes()


def manage_failover_new(control_console, passed_failover_params):
    current_failover_params, _ = control_console.eval_res_err('''
        return require('cartridge').failover_get_params()
    ''')

    mode = passed_failover_params['mode']

    failover_params = {
        'mode': mode,
    }

    if mode == 'stateful':
        state_provider = passed_failover_params.get('state_provider')
        if state_provider == 'stateboard':
            failover_params['state_provider'] = 'tarantool'
        else:
            failover_params['state_provider'] = state_provider

    stateboard_params = passed_failover_params.get('stateboard_params')
    if stateboard_params:
        failover_params['tarantool_params'] = stateboard_params

    etcd2_params = passed_failover_params.get('etcd2_params')
    if etcd2_params:
        failover_params['etcd2_params'] = etcd2_params

    func_body = '''
        return require('cartridge').failover_set_params(...)
    '''
    res, err = control_console.eval_res_err(func_body, failover_params)

    if err is not None:
        errmsg = 'Failed to set failover params: {}'.format(err)
        return helpers.ModuleRes(failed=True, msg=errmsg)

    new_failover_params, _ = control_console.eval_res_err('''
        return require('cartridge').failover_get_params()
    ''')

    changed = new_failover_params != current_failover_params
    return helpers.ModuleRes(changed=changed)


def manage_failover(params):
    failover_params = params.get('failover_params')

    if isinstance(failover_params, bool):
        failover_params = {
            'mode': 'eventual' if failover_params is True else 'disabled'
        }

    control_console = helpers.get_control_console(params['console_sock'])

    helpers.set_twophase_options_from_params(control_console, params)

    version = get_tarantool_version(control_console)
    if version is not None and version >= NEW_FAILOVER_API_CARTRIDGE_VERSION:
        return manage_failover_new(control_console, failover_params)
    else:
        if failover_params['mode'] == 'stateful':
            errmsg = 'Stateful failover is supported since cartridge {}'.format(
                NEW_FAILOVER_API_CARTRIDGE_VERSION
            )
            return helpers.ModuleRes(failed=True, msg=errmsg)
        return manage_failover_old(control_console, failover_params)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, manage_failover)
