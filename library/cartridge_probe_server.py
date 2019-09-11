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


def probe_server(params):
    if 'http_port' not in params['instance']:
       params['instance']['http_port'] = '8080'

    changed = False

    # Get instance URI
    admin_api_url = 'http://{}:{}/admin/api'.format(
        params['server_address'],
        params['instance']['http_port']
    )

    query = '''
        query {
          cluster {
            self {
              uri
            }
          }
        }
    '''

    response = requests.post(admin_api_url, json={'query': query})
    err = check_query_error(query, response)
    if err is not None:
        return err

    instance_uri = response.json()['data']['cluster']['self']['uri']

    # Probe instance
    ## NOTE: control instance is used here
    admin_api_url = 'http://{}:{}/admin/api'.format(
        params['control_instance_address'],
        params['control_instance_port']
    )
    query = '''
        mutation {{
          probe_instance:
            probe_server(uri: "{}")
        }}
    '''.format(instance_uri)

    response = requests.post(admin_api_url, json={'query': query})
    err = check_query_error(query, response)
    if err is not None:
        return err

    probe_success = response.json()['data']['probe_instance']
    return ModuleRes(success=probe_success, changed=changed)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = probe_server(module.params)

    if res.success == True:
        module.exit_json(changed=res.changed)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
