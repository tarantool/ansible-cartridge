#!/usr/bin/env python

import os

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'config': {'required': True, 'type': 'dict'},
    'cartridge_defaults': {'required': False, 'type': 'dict', 'default': {}},
}


def is_dynamic_param(param_name):
    return param_name in helpers.DYNAMIC_BOX_CFG_PARAMS


def is_memory_size_param(param_name):
    return param_name in helpers.MEMORY_SIZE_BOX_CFG_PARAMS


def change_memory_size(current_box_cfg, param_name, cartridge_defaults, config, control_console):
    new_memory_size = config.get(param_name, cartridge_defaults.get(param_name))

    if new_memory_size is None:
        return False, None

    # Get current memory size
    current_memory_size = current_box_cfg.get(param_name)

    if current_memory_size is None:
        # box.cfg wasn't called
        return False, None

    if new_memory_size <= current_memory_size:
        return False, None

    # try to increase memory size
    func_body = '''
        local param_name, new_memory_size = ...
        local ok, err = pcall(function()
            box.cfg {
                [param_name] = new_memory_size
            }
        end)
        if not ok then
            if tostring(err):find("cannot decrease memory size at runtime") == nil then
                return nil, string.format('failed to set %s: %s', param_name, err)
            end
        end
        return ok
    '''
    ok, err = control_console.eval_res_err(func_body, param_name, new_memory_size)
    if not ok:
        return False, err

    return True, None


def change_dynamic_params(current_box_cfg, cartridge_defaults, config, control_console):
    params = dict()

    for param_name, param_value in config.items():
        if is_dynamic_param(param_name) and not is_memory_size_param(param_name):
            params.update({param_name: param_value})

    for param_name, param_value in cartridge_defaults.items():
        if param_name in params:
            continue
        if is_dynamic_param(param_name) and not is_memory_size_param(param_name):
            params.update({param_name: param_value})

    if not params:
        return False

    func_body = '''
        box.cfg(...)
        return box.cfg
    '''
    new_box_cfg, _ = control_console.eval_res_err(func_body, params)

    changed = new_box_cfg != current_box_cfg
    return changed


def manage_instance(params):
    config = params['config']
    cartridge_defaults = params['cartridge_defaults']
    console_sock = params['console_sock']

    # Check if instance isn't started yet
    if not os.path.exists(console_sock):
        return helpers.ModuleRes(changed=False)

    try:
        control_console = helpers.get_control_console(console_sock)
    except helpers.CartridgeException as e:
        allowed_errcodes = [
            helpers.CartridgeErrorCodes.SOCKET_NOT_FOUND,
            helpers.CartridgeErrorCodes.FAILED_TO_CONNECT_TO_SOCKET,
            helpers.CartridgeErrorCodes.INSTANCE_IS_NOT_STARTED_YET
        ]
        if e.code in allowed_errcodes:
            return helpers.ModuleRes(changed=False)

        raise e

    if not helpers.box_cfg_was_called(control_console):
        return helpers.ModuleRes(changed=False)

    current_box_cfg = helpers.get_box_cfg(control_console)

    # Change memory size
    memory_size_changed = False

    for param_name in helpers.MEMORY_SIZE_BOX_CFG_PARAMS:
        if param_name in config or param_name in cartridge_defaults:
            memory_param_changed, err = change_memory_size(
                current_box_cfg, param_name, cartridge_defaults, config, control_console
            )

            if err is not None:
                return helpers.ModuleRes(failed=True, msg="Failed to change memory size in runtime: %s" % err)

            memory_size_changed = memory_size_changed or memory_param_changed

    # Change dynamic params
    dynamic_params_changed = change_dynamic_params(current_box_cfg, cartridge_defaults, config, control_console)

    changed = memory_size_changed or dynamic_params_changed

    return helpers.ModuleRes(changed=changed)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, manage_instance)
