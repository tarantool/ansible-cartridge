#!/usr/bin/python

import requests

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, check_query
from ansible.module_utils.helpers import get_all_instances_info, get_instance_info


argument_spec = {
    'instance': {'required': True, 'type': 'dict'},
    'instance_address': {'required': True, 'type': 'str'},
    'control_instance_address': {'required': True, 'type': 'str'},
    'control_instance_port': {'required': True, 'type': 'str'},
}


def join_replicas(params):
    if 'replica_for' not in params['instance']:
        return ModuleRes(success=True, changed=False)

    leader_name = params['instance']['replica_for']
    ok, instances_info = get_all_instances_info(
        params['control_instance_address'], params['control_instance_port']
    )
    if not ok:
        return instances_info

    # Find target replicaset
    target_replicaset = None
    errmsg = None
    for i in instances_info:
        if i['alias'] == leader_name:
            if i['replicaset']['uuid'] is None:
                errmsg = 'Error joining {0} to {1}: {1} is not configured.'.format(
                    params['instance']['name'],
                    leader_name,
                )
                return ModuleRes(success=False, msg=errmsg)

            target_replicaset = i['replicaset']
            break

    if target_replicaset is None:
        errmsg = 'Error joining {0} to {1}: {1} instance not found.'.format(
            params['instance']['name'],
            leader_name,
        )
        return ModuleRes(success=False, msg=errmsg)

    # Get instance info
    ok, instance_info = get_instance_info(
        params['instance_address'], params['instance']['http_port'],
        params['control_instance_address'], params['control_instance_port']
    )
    if not ok:
        return instance_info

    if instance_info['uuid'] is not None:
        # Already joined
        if instance_info['replicaset']['uuid'] == target_replicaset['uuid']:
            # Already joined to this replicaset
            return ModuleRes(success=True, changed=False)

        # Joined to other replicaset
        errmsg = 'Error joining {0} to {1}: {0} is already joined.'.format(
            params['instance']['name'],
            leader_name,
        )
        return ModuleRes(success=False, msg=errmsg)

    # Join replica
    ## NOTE: control instance is used here
    control_instance_admin_api_url = 'http://{}:{}/admin/api'.format(
        params['control_instance_address'],
        params['control_instance_port']
    )

    query = '''
        mutation {{
            join_replica:
                join_server(
                    uri: "{}",
                    replicaset_uuid: "{}"
                )
        }}
    '''.format(instance_info['uri'], target_replicaset['uuid'])

    response = requests.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return err

    join_success = response.json()['data']['join_replica']

    return ModuleRes(success=join_success, changed=False)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = join_replicas(module.params)

    if res.success == True:
        module.exit_json(changed=res.changed)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
