#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule

from ansible.module_utils.helpers import ModuleRes
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

    return ModuleRes(changed=False, facts={
        'not_expelled_instance': {
            'name': not_expelled_instance_name,
            'console_sock': instance_info['console_sock'],
        }
    })


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = get_one_not_expelled_instance(module.params)
    except Exception as e:
        res = ModuleRes(exception=e)
    res.exit(module)


if __name__ == '__main__':
    main()
