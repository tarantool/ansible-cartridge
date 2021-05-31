#!/usr/bin/env python

from copy import deepcopy

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'instance_config': {'required': True, 'type': 'dict'},
    'cartridge_defaults': {'required': False, 'type': 'dict', 'default': {}},
}


def change_memory_size(control_console, param_name, old_value, new_value):
    if old_value is None or new_value is None or new_value <= old_value:
        return False, None

    increase_memory_func_body = '''
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
    return control_console.eval_res_err(increase_memory_func_body, param_name, new_value)


def change_dynamic_params(control_console, old_config, new_config):
    memory_changed = False
    params_to_change = {}

    for param_name, new_value in new_config.items():
        old_value = old_config.get(param_name)

        if param_name in helpers.MEMORY_SIZE_BOX_CFG_PARAMS:
            changed, err = change_memory_size(control_console, param_name, old_value, new_value)
            if err is not None:
                return None, 'Failed to change memory size in runtime: %s' % err
            if changed:
                memory_changed = True

        elif param_name in helpers.DYNAMIC_BOX_CFG_PARAMS and new_value != old_value:
            params_to_change.update({param_name: new_value})

    if not params_to_change:
        return memory_changed, None

    update_box_cfg_func_body = '''
        box.cfg(...)
        return box.cfg
    '''
    updated_config, _ = control_console.eval_res_err(update_box_cfg_func_body, params_to_change)

    return memory_changed or updated_config != old_config, None


def configure_box_cfg_params(console_sock, instance_config, defaults=None):
    control_console, _ = helpers.get_control_console_if_started(console_sock)
    if not control_console:
        return False, None

    if not helpers.box_cfg_was_called(control_console):
        return False, None

    old_config = helpers.get_box_cfg(control_console)
    new_config = deepcopy(defaults or {})
    new_config.update(instance_config)

    return change_dynamic_params(control_console, old_config, new_config)


def configure_instance(params):
    console_sock = params['console_sock']
    instance_config = params['instance_config']
    cartridge_defaults = params['cartridge_defaults']

    changed, error = configure_box_cfg_params(console_sock, instance_config, cartridge_defaults)
    if error is not None:
        return helpers.ModuleRes(failed=True, msg=error)
    return helpers.ModuleRes(changed=changed)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, configure_instance)
