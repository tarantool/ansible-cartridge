#!/usr/bin/python

import requests

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, check_query
from ansible.module_utils.helpers import get_authorized_session, boolean_to_graphql_string
from ansible.module_utils.helpers import get_cluster_auth_params, edit_cluster_auth_params


argument_spec = {
    'auth_params': {'required': True, 'type': 'dict'},
    'control_instance_address': {'required': True, 'type': 'str'},
    'control_instance_port': {'required': True, 'type': 'str'},
    'cluster_cookie': {'required': True, 'type': 'str'},
}


def manage_auth_params(params):
    auth_params = params['auth_params']
    if not auth_params:
        return ModuleRes(success=True, changed=False)

    session = get_authorized_session(params['cluster_cookie'])

    control_instance_admin_api_url = 'http://{}:{}/admin/api'.format(
        params['control_instance_address'],
        params['control_instance_port']
    )

    ok, cluster_auth_params = get_cluster_auth_params(control_instance_admin_api_url, session)
    if not ok:
        return cluster_auth_params

    ok, new_cluster_auth_params = edit_cluster_auth_params(
        control_instance_admin_api_url, session,
        enabled=auth_params['enabled'] if 'enabled' in auth_params else None,
        cookie_max_age=auth_params['cookie_max_age'] if 'cookie_max_age' in auth_params else None,
        cookie_renew_age=auth_params['cookie_renew_age'] if 'cookie_renew_age' in auth_params else None,
    )
    if not ok:
        return new_cluster_auth_params

    changed = new_cluster_auth_params != cluster_auth_params
    return ModuleRes(success=True, changed=changed)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = manage_auth_params(module.params)

    if res.success == True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
