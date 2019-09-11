#!/usr/bin/python

import requests

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, check_query_error


argument_spec = {
    'instance': {'required': True, 'type': 'dict'},
    'server_address': {'required': True, 'type': 'str'},
    'control_instance_address': {'required': True, 'type': 'str'},
    'control_instance_port': {'required': True, 'type': 'str'},
}


def join_replicas(params):
    if 'replica_for' not in params['instance']:
        return ModuleRes(success=True, changed=False)

    leader_name = params['instance']['replica_for']

    # Get all instances list
    query = '''
        query {
          servers {
            alias
            replicaset {
              uuid
            }
          }
        }
    '''

    admin_api_url = 'http://{}:{}/admin/api'.format(params['control_instance_address'], params['control_instance_port'])
    response = requests.post(admin_api_url, json={'query': query})
    err = check_query_error(query, response)
    if err is not None:
        return err

    instances = response.json()['data']['servers']

    # Find target replicaset
    target_replicaset = None
    errmsg = None
    for i in instances:
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

    # Get instance UUID and URI (to check if it is already joined)
    query = '''
        query {
          cluster {
            self {
              uuid
              uri
            }
          }
        }
    '''

    admin_api_url = 'http://{}:{}/admin/api'.format(params['server_address'], params['instance']['http_port'])
    response = requests.post(admin_api_url, json={'query': query})
    err = check_query_error(query, response)
    if err is not None:
        return err

    instance_uuid = response.json()['data']['cluster']['self']['uuid']
    instance_uri = response.json()['data']['cluster']['self']['uri']

    if instance_uuid is not None:
        # Get instance replicaset UUID to check if it already joined to target server
        query = '''
            query {{
                servers(uuid: "{}") {{
                    replicaset {{
                        uuid
                    }}
                }}
            }}
        '''.format(instance_uuid)

        admin_api_url = 'http://{}:{}/admin/api'.format(params['control_instance_address'], params['control_instance_port'])
        response = requests.post(admin_api_url, json={'query': query})
        err = check_query_error(query, response)
        if err is not None:
            return err

        instance_replicaset = response.json()['data']['servers'][0]['replicaset']
        if instance_replicaset['uuid'] is not None:
            if instance_replicaset['uuid'] == target_replicaset['uuid']:
                # Already joined to this replicaset
                return ModuleRes(success=True, changed=False)

            errmsg = 'Error joining {0} to {1}: {0} is already joined.'.format(
                params['instance']['name'],
                leader_name,
            )
            return ModuleRes(success=False, msg=errmsg)

    # Join replica
    query = '''
        mutation {{
            join_replica:
                join_server(
                    uri: "{}",
                    replicaset_uuid: "{}"
                )
        }}
    '''.format(instance_uri, target_replicaset['uuid'])

    admin_api_url = 'http://{}:{}/admin/api'.format(params['control_instance_address'], params['control_instance_port'])
    response = requests.post(admin_api_url, json={'query': query})
    err = check_query_error(query, response)
    if err is not None:
        return err

    join_success = response.json()['data']['join_replica']

    return ModuleRes(success=join_success, changed=False, meta=instances)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = join_replicas(module.params)

    if res.success == True:
        module.exit_json(changed=res.changed)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
