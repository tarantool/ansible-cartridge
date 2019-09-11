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


def probe_server(params):
    if 'http_port' not in params['instance']:
       params['instance']['http_port'] = '8080'

    changed = False

    # Get instance info
    ok, instance_info = get_instance_info(
        params['instance_address'], params['instance']['http_port'],
        params['control_instance_address'], params['control_instance_port']
    )
    if not ok:
        return instance_info

    # Probe instance
    ## NOTE: control instance is used here
    control_instance_admin_api_url = 'http://{}:{}/admin/api'.format(
        params['control_instance_address'],
        params['control_instance_port']
    )

    query = '''
        mutation {{
          probe_instance:
            probe_server(uri: "{}")
        }}
    '''.format(instance_info['uri'])

    response = requests.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
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
