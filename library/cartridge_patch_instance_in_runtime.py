#!/usr/bin/env python

from copy import deepcopy

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'instance_config': {'required': True, 'type': 'dict'},
    'cartridge_defaults': {'required': False, 'type': 'dict', 'default': {}},
    'strict_mode': {'required': False, 'type': 'bool', 'default': False},
}


def change_memory_size(control_console, param_name, new_value):
    if new_value is None:
        return False, None

    increase_memory_func_body = '''
        local param_name, new_memory_size = ...
        local ok, err = pcall(box.cfg, { [param_name] = new_memory_size })
        if not ok then
            if tostring(err):find("cannot decrease memory size at runtime") == nil then
                return nil, string.format('failed to set %s: %s', param_name, err)
            end
        end
        return ok
    '''
    return control_console.eval_res_err(increase_memory_func_body, param_name, new_value)


def change_dynamic_params(control_console, old_box_config, new_config, strict_mode=False):
    memory_sizes_to_change = {}
    box_params_to_change = {}
    incorrect_params_errors = []

    for param_name, new_value in new_config.items():
        old_box_value = old_box_config.get(param_name)

        if param_name in helpers.MEMORY_SIZE_BOX_CFG_PARAMS:
            if new_value > old_box_value:
                memory_sizes_to_change.update({param_name: new_value})
            else:
                incorrect_params_errors.append("impossible to change '%s' from '%s' to '%s' in runtime" % (
                    param_name, old_box_value, new_value,
                ))

        elif param_name in helpers.DYNAMIC_BOX_CFG_PARAMS:
            if new_value != old_box_value:
                box_params_to_change.update({param_name: new_value})

        else:
            incorrect_params_errors.append("impossible to change '%s' in runtime" % param_name)

    if strict_mode and incorrect_params_errors:
        return None, ','.join(incorrect_params_errors)

    memory_changed = False
    for param_name, new_value in memory_sizes_to_change.items():
        changed, err = change_memory_size(control_console, param_name, new_value)
        if err is not None:
            return None, 'Failed to change memory size in runtime: %s' % err
        if changed:
            memory_changed = True

    box_changed = False
    if box_params_to_change:
        update_box_cfg_func_body = '''
            box.cfg(...)
            return box.cfg
        '''
        updated_config, _ = control_console.eval_res_err(update_box_cfg_func_body, box_params_to_change)
        box_changed = old_box_config != updated_config

    return memory_changed or box_changed, None


def configure_box_cfg_params(console_sock, instance_config, defaults=None, strict_mode=False):
    control_console, err = helpers.get_control_console_if_started(console_sock)
    if err is not None:
        return None, err
    if not control_console:
        return False, None

    if not helpers.box_cfg_was_called(control_console):
        return False, None

    old_box_config = helpers.get_box_cfg(control_console)
    new_config = deepcopy(defaults or {})
    new_config.update(instance_config)

    return change_dynamic_params(control_console, old_box_config, new_config, strict_mode)


def patch_instance_in_runtime(params):
    console_sock = params['console_sock']
    instance_config = params['instance_config']
    cartridge_defaults = params['cartridge_defaults']
    strict_mode = params['strict_mode']

    changed, error = configure_box_cfg_params(console_sock, instance_config, cartridge_defaults, strict_mode)
    if error is not None:
        return helpers.ModuleRes(failed=True, msg=error)
    return helpers.ModuleRes(changed=changed)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, patch_instance_in_runtime)
