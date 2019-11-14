#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import instance_expelled


argument_spec = {
    'hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
    'control_host': {'required': True, 'type': 'str'},
}


def get_replicasets(params):
    hostvars = params['hostvars']
    play_hosts = params['play_hosts']

    replicasets = {}
    for i, instance_vars in hostvars.items():
        if i not in play_hosts:
            continue

        if instance_expelled(instance_vars):
            continue

        if 'replicaset_alias' in instance_vars:
            replicaset_alias = instance_vars['replicaset_alias']
            if replicaset_alias not in replicasets:
                replicasets.update({
                    replicaset_alias: {
                        'instances': [],
                        'roles': instance_vars['roles'] if 'roles' in instance_vars else None,
                        'leader': instance_vars['leader'] if 'leader' in instance_vars else None,
                        'all_rw': instance_vars['all_rw'] if 'all_rw' in instance_vars else None,
                        'weight': instance_vars['weight'] if 'weight' in instance_vars else None,
                        'alias': replicaset_alias,
                    }
                })
            replicasets[replicaset_alias]['instances'].append(i)

    join_host = params['control_host']
    replicasets_list = [v for _, v in replicasets.items()]

    if not join_host:
        join_host = replicasets_list[0]['leader'] if replicasets_list else None

    return ModuleRes(success=True, changed=False, meta={
        'replicasets': replicasets_list,
        'join_host': join_host,
    })


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = get_replicasets(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
