#!/usr/bin/python

import pkgutil

if pkgutil.find_loader('ansible.module_utils.helpers'):
    import ansible.module_utils.helpers as helpers
else:
    import module_utils.helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
}


def probe_server(control_console, uri):
    return control_console.eval_res_err('''
        local advertise_uri = ...
        if require('membership').get_member(advertise_uri) ~= nil then
            return false
        end
        return require('cartridge').admin_probe_server(advertise_uri)
    ''', uri)


def connect_to_membership(params):
    control_console = helpers.get_control_console(params['console_sock'])
    hostvars = params['hostvars']
    play_hosts = params['play_hosts']

    changed = False

    for instance_name, instance_vars in hostvars.items():
        if helpers.is_expelled(instance_vars) or helpers.is_stateboard(instance_vars):
            continue

        if 'config' not in instance_vars or 'advertise_uri' not in instance_vars['config']:
            continue

        connected, err = probe_server(control_console, instance_vars['config']['advertise_uri'])
        if err is not None and instance_name in play_hosts:
            return helpers.ModuleRes(failed=True, msg=err)

        if connected:
            changed = True

    return helpers.ModuleRes(changed=changed)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, connect_to_membership)
