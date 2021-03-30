#!/usr/bin/python


from ansible.module_utils.helpers import execute_module, ModuleRes
from ansible.module_utils.helpers import is_expelled, is_stateboard

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
        if is_expelled(instance_vars) or is_stateboard(instance_vars):
            continue

        not_expelled_instance_name = instance_name
        break

    if not_expelled_instance_name is None:
        errmsg = "Not found any instance that is not expelled and is not a stateboard"
        return ModuleRes(failed=True, msg=errmsg)

    instance_info = hostvars[not_expelled_instance_name]['instance_info']

    return ModuleRes(changed=False, fact={
        'name': not_expelled_instance_name,
        'console_sock': instance_info['console_sock'],
    })


if __name__ == '__main__':
    execute_module(argument_spec, get_one_not_expelled_instance)
