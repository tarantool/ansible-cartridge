#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException


argument_spec = {
    'hostvars': {'required': True, 'type': 'dict'},
}


def setup_replicaset(params):
    hostvars = params['hostvars']

    replicasets = {}
    for i, instance_vars in hostvars.items():
        if 'replicaset_alias' in instance_vars:
            replicaset_alias = instance_vars['replicaset_alias']
            if replicaset_alias not in replicasets:
                replicasets.update({
                    replicaset_alias: {
                        'instances': [],
                        'roles': instance_vars['roles'] if 'roles' in instance_vars else None,
                        'leader': instance_vars['leader'] if 'leader' in instance_vars else None,
                        'alias': replicaset_alias,
                    }
                })
            replicasets[replicaset_alias]['instances'].append(i)

    replicasets_list = [v for _, v in replicasets.items()]
    join_host = replicasets_list[0]['leader'] if replicasets_list else None

    return ModuleRes(success=True, changed=False, meta={
        'replicasets': replicasets_list,
        'join_host': join_host,
    })


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = setup_replicaset(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
