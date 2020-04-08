#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException, cartridge_errcodes
from ansible.module_utils.helpers import get_control_console

import os


argument_spec = {
    'control_sock': {'required': True, 'type': 'str'},
    'config': {'required': True, 'type': 'dict'},
    'cartridge_defaults': {'required': True, 'type': 'dict'},
}


def manage_instance(params):
    config = params['config']
    cartridge_defaults = params['cartridge_defaults']
    control_sock = params['control_sock']

    # Check if memtx_memory parameter is specified
    if 'memtx_memory' not in config and 'memtx_memory' not in cartridge_defaults:
        return ModuleRes(success=True, changed=False)

    new_memtx_memory = None
    if 'memtx_memory' in config:
        new_memtx_memory = config['memtx_memory']
    else:
        new_memtx_memory = cartridge_defaults['memtx_memory']

    # Check if instance isn't started yet
    if not os.path.exists(control_sock):
        return ModuleRes(success=True, changed=False)

    try:
        control_console = get_control_console(control_sock)
    except CartridgeException as e:
        allowed_errcodes = [
            cartridge_errcodes.SOCKET_NOT_FOUND,
            cartridge_errcodes.FAILED_TO_CONNECT_TO_SOCKET,
            cartridge_errcodes.INSTANCE_IS_NOT_STARTED_YET
        ]
        if e.code in allowed_errcodes:
            return ModuleRes(success=True, changed=False)

        raise e

    # Get current memtx memory
    current_memtx_memory = control_console.eval('''
        return type(box.cfg) ~= 'function' and box.cfg.memtx_memory or box.NULL
    ''')
    if current_memtx_memory is None:
        # box.cfg wasn't called
        return ModuleRes(success=True, changed=False)

    if new_memtx_memory <= current_memtx_memory:
        return ModuleRes(success=True, changed=False)

    # try to increase memtx_memory
    increased = control_console.eval('''
        local ok, err = pcall(function()
            box.cfg {{ memtx_memory = {} }}
        end)
        if not ok then
            if tostring(err):find("cannot decrease memory size at runtime") == nil then
                error('failed to set memtx_memory: ' .. tostring(err))
            end
        end
        return ok
    '''.format(new_memtx_memory))

    return ModuleRes(success=True, changed=increased)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = manage_instance(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
