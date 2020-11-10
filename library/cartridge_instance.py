#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException, cartridge_errcodes
from ansible.module_utils.helpers import get_control_console
from ansible.module_utils.helpers import dynamic_box_cfg_params, memory_size_box_cfg_params

import os


argument_spec = {
    'control_sock': {'required': True, 'type': 'str'},
    'config': {'required': True, 'type': 'dict'},
    'cartridge_defaults': {'required': False, 'type': 'dict', 'default': {}},
}


def serialize_dict(d):
    parts = []

    for k, v in d.items():
        value_str = None
        if type(v) == str:
            value_str = "'%s'" % v
        elif type(v) == float or type(v) == int:
            value_str = "%s" % v
        elif type(v) == bool:
            value_str = 'true' if v else 'false'
        else:
            raise CartridgeException(
                cartridge_errcodes.BAD_VALUE_TYPE,
                "Unknown value type: {}" % type(v)
            )

        parts.append("%s = %s" % (k, value_str))

    return '{ %s }' % ', '.join(parts)


def box_cfg_was_called(control_console):
    return control_console.eval('''
        return type(box.cfg) ~= 'function'
    ''')


def get_box_cfg(control_console):
    return control_console.eval('''
        return type(box.cfg) == 'table' and box.cfg or box.NULL
    ''')


def is_dynamic_param(param_name):
    return param_name in dynamic_box_cfg_params


def is_memory_size_param(param_name):
    return param_name in memory_size_box_cfg_params


def change_memory_size(param_name, cartridge_defaults, config, control_console):
    new_memory_size = config.get(param_name, cartridge_defaults.get(param_name))

    if new_memory_size is None:
        return False

    # Get current memory size
    current_memory_size = control_console.eval('''
        return type(box.cfg) ~= 'function' and box.cfg.{} or box.NULL
    '''.format(param_name))

    if current_memory_size is None:
        # box.cfg wasn't called
        return False

    if new_memory_size <= current_memory_size:
        return False

    # try to increase memory size
    increased = control_console.eval('''
        local ok, err = pcall(function()
            box.cfg {{ {param_name} = {new_memory_size} }}
        end)
        if not ok then
            if tostring(err):find("cannot decrease memory size at runtime") == nil then
                error('failed to set {param_name}: ' .. tostring(err))
            end
        end
        return ok
    '''.format(param_name=param_name, new_memory_size=new_memory_size))

    return increased


def change_dynamic_params(cartridge_defaults, config, control_console):
    params = dict()

    # Get current values
    current_box_cfg = get_box_cfg(control_console)
    if current_box_cfg is None:
        return False

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

    serialized_params = serialize_dict(params)

    new_box_cfg = control_console.eval('''
        box.cfg({serialized_params})
        return box.cfg
    '''.format(serialized_params=serialized_params))

    changed = new_box_cfg != current_box_cfg
    return changed


def manage_instance(params):
    config = params['config']
    cartridge_defaults = params['cartridge_defaults']
    control_sock = params['control_sock']

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

    if not box_cfg_was_called(control_console):
        return ModuleRes(success=True, changed=False)

    # Change memory size
    memory_size_changed = False

    for param_name in memory_size_box_cfg_params:
        if param_name in config or param_name in cartridge_defaults:
            memory_size_changed = memory_size_changed or change_memory_size(
                param_name, cartridge_defaults, config, control_console
            )

    # Change dynamic params
    dynamic_params_changed = change_dynamic_params(cartridge_defaults, config, control_console)

    changed = memory_size_changed or dynamic_params_changed

    return ModuleRes(success=True, changed=changed)


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
