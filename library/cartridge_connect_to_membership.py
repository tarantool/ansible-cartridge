#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'module_hostvars': {'required': True, 'type': 'dict'},
    'cluster_disabled_instances': {'required': True, 'type': 'list'},
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
    module_hostvars = params['module_hostvars']
    cluster_disabled_instances = params['cluster_disabled_instances']
    play_hosts = params['play_hosts']

    changed = False

    for instance_name, instance_vars in module_hostvars.items():
        if any([
            helpers.is_stateboard(instance_vars),
            not helpers.is_enabled(instance_vars),
            instance_name in cluster_disabled_instances,
            'advertise_uri' not in instance_vars.get('config', {}),
        ]):
            continue

        connected, err = probe_server(control_console, instance_vars['config']['advertise_uri'])
        if err is not None and instance_name in play_hosts:
            return helpers.ModuleRes(failed=True, msg=err)

        if connected:
            changed = True

    return helpers.ModuleRes(changed=changed)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, connect_to_membership)
