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


def probe_server(params):
    control_console = helpers.get_control_console(params['console_sock'])
    hostvars = params['hostvars']
    play_hosts = params['play_hosts']

    for i, instance_vars in hostvars.items():
        if 'config' not in instance_vars:
            continue

        if helpers.is_expelled(instance_vars) or helpers.is_stateboard(instance_vars):
            continue

        advertise_uri = instance_vars['config']['advertise_uri']
        func_body = '''
            local advertise_uri = ...
            return require('cartridge').admin_probe_server(advertise_uri)
        '''

        ok, err = control_console.eval_res_err(func_body, advertise_uri)

        if not ok and i in play_hosts:
            return helpers.ModuleRes(failed=True, msg=err)

    return helpers.ModuleRes(changed=False)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, probe_server)
