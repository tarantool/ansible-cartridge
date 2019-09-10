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
}

def probe_server(params):
    if 'http_port' not in params['instance']:
       params['instance']['http_port'] = '8080'

    changed = False
    admin_api_url = 'http://{}:{}/admin/api'.format(params['server_address'], params['instance']['http_port'])

    # Get instance URI
    query = '''
        query {
          cluster {
            self {
              uri
            }
          }
        }
    '''
    request = requests.post(admin_api_url, json={'query': query})
    if request.status_code != 200:
        return ModuleRes(success=False,
                         msg="Query failed to run by returning code of {}. {}".format(request.status_code, query))

    instance_uri = request.json()['data']['cluster']['self']['uri']

    # Probe instance
    query = '''
        mutation {{
          probe_instance:
            probe_server(uri: "{}")
        }}
    '''.format(instance_uri)
    request = requests.post(admin_api_url, json={'query': query})
    if request.status_code != 200:
        return ModuleRes(success=False,
                         msg="Query failed to run by returning code of {}. {}".format(request.status_code, query))

    probe_success = request.json()['data']['probe_instance']
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
