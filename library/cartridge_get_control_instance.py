#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console
from ansible.module_utils.helpers import is_expelled, is_stateboard

argument_spec = {
    'hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
    'console_sock': {'requires': True, 'type': 'str'},
}


def get_control_instance(params):
    hostvars = params['hostvars']
    play_hosts = params['play_hosts']
    console_sock = params['console_sock']

    control_console = get_control_console(console_sock)
    control_instance_name = None

    members, _ = control_console.eval_res_err('''
        return require('membership').members()
    ''')

    for _, member in members.items():
        if 'payload' in member and member['payload'].get('uuid') is not None:
            if member['payload'].get('alias') is None:
                errmsg = 'Unable to get instance alias for "{}"'.format(member['payload']['uuid'])
                return ModuleRes(success=False, msg=errmsg)

            instance_name = member['payload']['alias']
            control_instance_name = instance_name
            break

    if control_instance_name is None:
        for instance_name in play_hosts:
            instance_vars = hostvars[instance_name]
            if is_expelled(instance_vars) or is_stateboard(instance_vars):
                continue

            if 'replicaset_alias' in instance_vars:
                control_instance_name = instance_name
                break

    if control_instance_name is None:
        errmsg = 'Not found any joined instance or instance to create a replicaset'
        return ModuleRes(success=False, msg=errmsg)

    instance_vars = hostvars[control_instance_name]
    if 'instance_info' not in instance_vars:
        raise Exception('Instance %s has no instance_info set' % control_instance_name)

    instance_info = instance_vars['instance_info']
    control_instance = {
        'name': control_instance_name,
        'console_sock': instance_info['console_sock'],
    }

    return ModuleRes(success=True, meta=control_instance)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = get_control_instance(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, **res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
