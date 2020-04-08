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
                        'roles': instance_vars.get('roles', None),
                        'failover_priority': instance_vars.get('failover_priority', None),
                        'all_rw': instance_vars.get('all_rw', None),
                        'weight': instance_vars.get('weight', None),
                        'vshard_group': instance_vars.get('vshard_group', None),
                        'alias': replicaset_alias,
                    }
                })
            replicasets[replicaset_alias]['instances'].append(i)

    join_host = params['control_host']
    replicasets_list = [v for _, v in replicasets.items()]

    for r in replicasets_list:
        if r['failover_priority'] is None:
            r['failover_priority'] = [r['instances'][0]]

    if replicasets_list and not join_host:
        first_replicaset = replicasets_list[0]
        join_host = first_replicaset['failover_priority'][0]

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
