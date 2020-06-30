#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console


argument_spec = {
    'control_sock': {'required': True, 'type': 'str'},
    'failover_params': {'required': False, 'type': 'raw'},
}


NEW_FAILOVER_API_CARTRIDGE_VERSION = '2.1.0'
DEFAULT_STATE_PROVIDER = 'tarantool'


def get_tarantool_version(control_console):
    version = control_console.eval('''
        return require('cartridge').VERSION or box.NULL
    ''')
    return version


def manage_failover_old(control_console, failover_params):
    failover_enabled = failover_params['mode'] == 'eventual'

    current_failover = control_console.eval('''
        return require('cartridge').admin_get_failover()
    ''')

    if current_failover == failover_enabled:
        return ModuleRes(success=True, changed=False)

    function_name = 'admin_enable_failover' if failover_enabled else 'admin_disable_failover'

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


def manage_failover_new(control_console, failover_params):
    current_failover_params = control_console.eval('''
        return require('cartridge').failover_get_params()
    ''')

    mode = failover_params['mode']

    lua_params = [
        'mode = "{}"'.format(mode)
    ]

    if mode == 'stateful':
        state_provider = failover_params.get('state_provider')
        if state_provider == 'stateboard':
            lua_params.append('state_provider = "tarantool"')

            stateboard_params = failover_params.get('stateboard_params')

            lua_stateboard_params = []
            if stateboard_params is not None:
                for string_param in ['uri', 'password']:
                    if stateboard_params.get(string_param) is not None:
                        lua_stateboard_params.append('{} = "{}"'.format(string_param, stateboard_params[string_param]))

            if lua_stateboard_params:
                lua_params.append('tarantool_params = {{ {} }}'.format(', '.join(lua_stateboard_params)))
        elif state_provider == 'etcd2':
            lua_params.append('state_provider = "etcd2"')

            etcd2_params = failover_params.get('etcd2_params')

            lua_etcd2_params = []
            if etcd2_params is not None:
                for string_param in ['prefix', 'username', 'password']:
                    if etcd2_params.get(string_param) is not None:
                        lua_etcd2_params.append('{} = "{}"'.format(string_param, etcd2_params[string_param]))

                if etcd2_params.get('lock_delay') is not None:
                    lua_etcd2_params.append('lock_delay = {}'.format(etcd2_params['lock_delay']))

                if etcd2_params.get('endpoints') is not None:
                    lua_etcd2_params.append('endpoints = {{ {} }}'.format(
                        ", ".join('"{}"'.format(endpoint) for endpoint in etcd2_params['endpoints'])
                    ))

            if lua_etcd2_params:
                lua_params.append('etcd2_params = {{ {} }}'.format(', '.join(lua_etcd2_params)))

    res = control_console.eval('''
        local ok, err = require('cartridge').failover_set_params({{
            {}
        }})

        return {{
            ok = ok ~= nil and ok or box.NULL,
            err = err and err.err or box.NULL,
        }}
    '''.format(', '.join(lua_params)))

    if not res['ok']:
        errmsg = 'Failed to set failover params: {}'.format(res['err'])
        return ModuleRes(success=False, msg=errmsg)

    new_failover_params = control_console.eval('''
        return require('cartridge').failover_get_params()
    ''')

    changed = new_failover_params != current_failover_params
    return ModuleRes(success=True, changed=changed)


def manage_failover(params):
    failover_params = params.get('failover_params')

    if isinstance(failover_params, bool):
        failover_params = {
            'mode': 'eventual' if failover_params is True else 'disabled'
        }

    control_console = get_control_console(params['control_sock'])
    version = get_tarantool_version(control_console)

    if version is not None and version >= NEW_FAILOVER_API_CARTRIDGE_VERSION:
        return manage_failover_new(control_console, failover_params)
    else:
        if failover_params['mode'] == 'stateful':
            errmsg = 'Stateful failover is supported since cartridge {}'.format(
                NEW_FAILOVER_API_CARTRIDGE_VERSION
            )
            return ModuleRes(success=False, msg=errmsg)
        return manage_failover_old(control_console, failover_params)


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
