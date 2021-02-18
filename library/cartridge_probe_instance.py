#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console
from ansible.module_utils.helpers import is_expelled, is_stateboard

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
}


def probe_server(params):
    control_console = get_control_console(params['console_sock'])
    hostvars = params['hostvars']
    play_hosts = params['play_hosts']

    for i, instance_vars in hostvars.items():
        if 'config' not in instance_vars:
            continue

        if is_expelled(instance_vars) or is_stateboard(instance_vars):
            continue

        advertise_uri = instance_vars['config']['advertise_uri']
        func_body = '''
            local advertise_uri = ...
            return require('cartridge').admin_probe_server(advertise_uri)
        '''

        ok, err = control_console.eval_res_err(func_body, advertise_uri)

        if not ok and i in play_hosts:
            return ModuleRes(failed=True, msg=err)

    return ModuleRes(changed=False)


def main():
    module = AnsibleModule(argument_spec=argument_spec)

    try:
        res = probe_server(module.params)
    except CartridgeException as e:
        res = ModuleRes(exception=e)
    res.exit(module)


if __name__ == '__main__':
    main()
