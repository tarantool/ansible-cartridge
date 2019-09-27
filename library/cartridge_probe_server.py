#!/usr/bin/python

import requests

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, check_query
from ansible.module_utils.helpers import get_instance_info, get_authorized_session


argument_spec = {
    'instance': {'required': True, 'type': 'dict'},
    'instance_address': {'required': True, 'type': 'str'},
    'control_instance_address': {'required': True, 'type': 'str'},
    'control_instance_port': {'required': True, 'type': 'str'},
    'cluster_cookie': {'required':True, 'type': 'str'},
}


def probe_server(params):
    if 'http_port' not in params['instance']:
       params['instance']['http_port'] = '8080'

    instance_admin_api_url = 'http://{}:{}/admin/api'.format(
        params['instance_address'],
        params['instance']['http_port'],
    )
    control_instance_admin_api_url = 'http://{}:{}/admin/api'.format(
        params['control_instance_address'],
        params['control_instance_port']
    )
    session = get_authorized_session(params['cluster_cookie'])

    # Get instance info
    ok, instance_info = get_instance_info(instance_admin_api_url, control_instance_admin_api_url, session)
    if not ok:
        return instance_info

    # Probe instance
    ## NOTE: control instance is used here
    query = '''
        mutation {{
          probe_instance:
            probe_server(uri: "{}")
        }}
    '''.format(instance_info['uri'])

    response = session.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return err

    probe_success = response.json()['data']['probe_instance']
    return ModuleRes(success=probe_success, changed=False)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = probe_server(module.params)

    if res.success == True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
