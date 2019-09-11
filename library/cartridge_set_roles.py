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


def set_roles(params):
    if 'roles' not in params['instance']:
        return ModuleRes(success=True, changed=False)

    if not params['instance']['roles']:
        return ModuleRes(success=False, msg='Instance roles list must be non-empty')

    admin_api_url = 'http://{}:{}/admin/api'.format(params['server_address'], params['instance']['http_port'])

    # Get instance URI and UUID
    query = '''
        query {
          cluster {
            self {
              uri
              uuid
            }
          }
        }
    '''
    response = requests.post(admin_api_url, json={'query': query})
    err = check_query_error(query, response)
    if err is not None:
        return err

    instance_uri = response.json()['data']['cluster']['self']['uri']
    instance_uuid = response.json()['data']['cluster']['self']['uuid']

    # Set roles
    ## NOTE: control instance is used here
    admin_api_url = 'http://{}:{}/admin/api'.format(params['control_instance_address'], params['control_instance_port'])

    if not instance_uuid:
        # Join instance with specified roles
        roles_str =  '[{}]'.format(', '.join(['"{}"'.format(role) for role in params['instance']['roles']]))
        query = '''
            mutation {{
                join_server(
                    uri: "{}",
                    roles: {}
                )
            }}
        '''.format(instance_uri, roles_str)
        response = requests.post(admin_api_url, json={'query': query})
        err = check_query_error(query, response)
        if err is not None:
            return err

        join_success = response.json()['data']['join_server']
        return ModuleRes(success=join_success, changed=join_success)

    # Edit replicaset
    return ModuleRes(success=True, changed=False)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = set_roles(module.params)

    if res.success == True:
        module.exit_json(changed=res.changed)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
