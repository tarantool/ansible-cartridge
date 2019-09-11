#!/usr/bin/python

import requests

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, check_query
from ansible.module_utils.helpers import get_instance_info


argument_spec = {
    'instance': {'required': True, 'type': 'dict'},
    'instance_address': {'required': True, 'type': 'str'},
    'control_instance_address': {'required': True, 'type': 'str'},
    'control_instance_port': {'required': True, 'type': 'str'},
}


def list_to_graphql_string(l):
    return '[{}]'.format(', '.join(['"{}"'.format(i) for i in l]))


def set_roles(params):
    if 'roles' not in params['instance']:
        return ModuleRes(success=True, changed=False)

    if not params['instance']['roles']:
        return ModuleRes(success=False, msg='Instance roles list must be non-empty')

    ok, instance_info = get_instance_info(
        params['instance_address'], params['instance']['http_port'],
        params['control_instance_address'], params['control_instance_port']
    )
    if not ok:
        return instance_info

    if instance_info['uuid'] is None:
        # Not joined yet
        ## NOTE: control instance is used here
        control_instance_admin_api_url = 'http://{}:{}/admin/api'.format(
            params['control_instance_address'],
            params['control_instance_port']
        )
        query = '''
            mutation {{
                join_server(
                    uri: "{}",
                    roles: {}
                )
            }}
        '''.format(instance_info['uri'], list_to_graphql_string(params['instance']['roles']))

        response = requests.post(control_instance_admin_api_url, json={'query': query})
        ok, err = check_query(query, response)
        if not ok:
            return err

        join_success = response.json()['data']['join_server']
        return ModuleRes(success=join_success, changed=join_success)

    # Instance is already joined
    if instance_info['replicaset']['roles'] == params['instance']['roles']:
        # Roles was not change
        return ModuleRes(success=True, changed=False)

    query = '''
        mutation {{
          edit_replicaset:
            edit_replicaset(uuid: "{}", roles: {})
        }}
    '''.format(instance_info['replicaset']['uuid'], list_to_graphql_string(params['instance']['roles']))

    response = requests.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return err

    return ModuleRes(success=True, changed=True)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = set_roles(module.params)

    if res.success == True:
        module.exit_json(changed=res.changed)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
