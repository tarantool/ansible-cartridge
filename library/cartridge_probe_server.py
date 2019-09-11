#!/usr/bin/python

import requests

from ansible.module_utils.basic import AnsibleModule

class ModuleRes:
    def __init__(self, success, msg=None, changed=False):
        self.success = success
        self.msg = msg
        self.changed = changed

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
    admin_api_url = 'http://{}:{}/admin/api'.format(params['server_address'], params['instance']['http_port'])
    print('admin_api_url')

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
    if response.status_code != 200:
        return ModuleRes(success=False,
                         msg="Query failed to run by returning code of {}. {}".format(response.status_code, query))
    if 'errors' in response.json():
        return ModuleRes(success=False,
                          msg="Query failed to run with error {}. {}".format(response.json()['errors'][0]['message'], query))

    instance_uri = response.json()['data']['cluster']['self']['uri']

    # Probe instance
    ## NOTE: control instance is used here
    admin_api_url = 'http://{}:{}/admin/api'.format(params['control_instance_address'], params['control_instance_port'])
    query = '''
        mutation {{
          probe_instance:
            probe_server(uri: "{}")
        }}
    '''.format(instance_uri)
    response = requests.post(admin_api_url, json={'query': query})
    if response.status_code != 200:
        return ModuleRes(success=False,
                         msg="Query failed to run by returning code of {}. {}".format(response.status_code, query))
    if 'errors' in response.json():
        return ModuleRes(success=False,
                          msg="Query failed to run with error {}. {}".format(response.json()['errors'][0]['message'], query))

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
