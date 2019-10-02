#!/usr/bin/python

import requests

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, check_query
from ansible.module_utils.helpers import get_all_instances_info
from ansible.module_utils.helpers import get_replicaset_info, wait_for_replicaset_is_healthy
from ansible.module_utils.helpers import list_to_graphql_string, get_authorized_session


argument_spec = {
    'replicaset': {'required': True, 'type': 'dict'},
    'control_instance_address': {'required': True, 'type': 'str'},
    'control_instance_port': {'required': True, 'type': 'str'},
    'cluster_cookie': {'required': True, 'type': 'str'},
}


def create_replicaset(control_instance_admin_api_url, session, params):
    replicaset = params['replicaset']
    # sanity checks
    if len(replicaset['instances']) == 1 and 'leader' not in replicaset:
        replicaset['leader'] = replicaset['instances'][0]

    if 'leader' not in replicaset:
        return ModuleRes(success=False, msg='Replicaset leader must be specified')

    if replicaset['leader'] not in replicaset['instances']:
        return ModuleRes(success=False, msg='Replicaset leader must be one of replicaset instances')

    # Check if all instances are started and not configured
    ok, instances_info = get_all_instances_info(control_instance_admin_api_url, session)
    if not ok:
        return instances_info
    instances_info = {i['alias']: i for i in instances_info}  # make it dict

    # Cerate replicaset (join leader)
    leader_instance_info = instances_info[replicaset['leader']]
    query = '''
        mutation {{
            join_server(
                uri: "{}"
                roles: {}
                replicaset_alias: "{}"
            )
        }}
    '''.format(
        leader_instance_info['uri'],
        list_to_graphql_string(params['replicaset']['roles']),
        replicaset['name']
    )

    response = requests.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return err
    join_success = response.json()['data']['join_server']
    if not join_success:
        return ModuleRes(success=False, msg='Failed to create replicaset')

    # Wait for replicaset is healthy
    ok = wait_for_replicaset_is_healthy(control_instance_admin_api_url, session, replicaset['name'])
    if not ok:
        errmsg = 'Replicaset "{}" is not healthy'.format(replicaset['name'])
        return ModuleRes(success=False, msg=errmsg)

    # Get replicaset UUID
    ok, replicaset_info = get_replicaset_info(control_instance_admin_api_url, session, params['replicaset']['name'])
    if not ok:
        return replicaset_info

    replicaset_uuid = replicaset_info['uuid']

    # Remove leader from instances list
    replicaset_instances = replicaset['instances']
    replicaset_instances.remove(replicaset['leader'])

    # Join other instances
    for replicaset_instance in replicaset_instances:
        replicaset_instance_info = instances_info[replicaset_instance]
        query = '''
            mutation {{
                join_server(
                    uri: "{}",
                    replicaset_uuid: "{}"
                )
            }}
        '''.format(replicaset_instance_info['uri'], replicaset_uuid)

        response = requests.post(control_instance_admin_api_url, json={'query': query})
        ok, err = check_query(query, response)
        if not ok:
            return err

        join_success = response.json()['data']['join_server']
        if not join_success:
            errmsg = 'Failed to join "{}"'.format(replicaset_instance_info['name'])
            return ModuleRes(success=False, msg=errmsg)

        # Wait for replicaset is healthy
        ok = wait_for_replicaset_is_healthy(control_instance_admin_api_url, session, replicaset['name'])
        if not ok:
            errmsg = 'Replicaset "{}" is not healthy'.format(replicaset['name'])
            return ModuleRes(success=False, msg=errmsg)

    return ModuleRes(success=True, changed=True)


def setup_replicaset(params):
    # Sanity checks
    if 'name' not in params['replicaset']:
        return ModuleRes(success=False, msg='Replicaset name must be specified')

    if 'instances' not in params['replicaset']:
        return ModuleRes(success=False, msg='Replicaset instances must be specified')

    if 'roles' not in params['replicaset']:
        return ModuleRes(success=False, msg='Replicaset roles must be specified')

    if not params['replicaset']['roles']:
        return ModuleRes(success=False, msg='Replicaset must have at least one role')

    control_instance_admin_api_url = 'http://{}:{}/admin/api'.format(
        params['control_instance_address'],
        params['control_instance_port']
    )

    session = get_authorized_session(params['cluster_cookie'])

    # Check if replicaset is already created
    ok, replicaset_info = get_replicaset_info(
        control_instance_admin_api_url,
        session,
        params['replicaset']['name']
    )
    if not ok:
        return replicaset_info

    if replicaset_info is None:
        return create_replicaset(control_instance_admin_api_url, session, params)

    return ModuleRes(success=True, changed=False)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = setup_replicaset(module.params)

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
