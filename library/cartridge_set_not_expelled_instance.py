#!/usr/bin/python

import pkgutil

if pkgutil.find_loader('ansible.module_utils.helpers'):
    import ansible.module_utils.helpers as helpers
else:
    import module_utils.helpers as helpers

argument_spec = {
    'hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
}


def get_one_not_expelled_instance(params):
    hostvars = params['hostvars']
    play_hosts = params['play_hosts']

    not_expelled_instance_name = None

    for instance_name in play_hosts:
        instance_vars = hostvars[instance_name]
        if helpers.is_expelled(instance_vars) or helpers.is_stateboard(instance_vars):
            continue

        not_expelled_instance_name = instance_name
        break

    if not_expelled_instance_name is None:
        errmsg = "Not found any instance that is not expelled and is not a stateboard"
        return helpers.ModuleRes(failed=True, msg=errmsg)

    instance_info = hostvars[not_expelled_instance_name]['instance_info']

    return helpers.ModuleRes(changed=False, facts={
        'not_expelled_instance': {
            'name': not_expelled_instance_name,
            'console_sock': instance_info['console_sock'],
        }
    })


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_one_not_expelled_instance)
