#!/usr/bin/python

import requests

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, check_query
from ansible.module_utils.helpers import get_authorized_session
from ansible.module_utils.helpers import get_cluster_auth_params, edit_cluster_auth_params
from ansible.module_utils.helpers import get_cluster_users, check_cluster_auth_implements_all
from ansible.module_utils.helpers import add_cluster_user, delete_cluster_user, edit_cluster_user


argument_spec = {
    'auth_params': {'required': True, 'type': 'dict'},
    'control_instance_address': {'required': True, 'type': 'str'},
    'control_instance_port': {'required': True, 'type': 'str'},
    'cluster_cookie': {'required': True, 'type': 'str'},
}


def user_is_deleted(user):
    return 'deleted' in user and user['deleted'] is True


def manage_auth_params(params):
    auth_params = params['auth_params']

    if not auth_params:
        return ModuleRes(success=True, changed=False)

    session = get_authorized_session(params['cluster_cookie'])

    control_instance_admin_api_url = 'http://{}:{}/admin/api'.format(
        params['control_instance_address'],
        params['control_instance_port']
    )

    # Check if auth backeng implements all functions for users managing
    if 'users' in auth_params:
        ok, err = check_cluster_auth_implements_all(control_instance_admin_api_url, session)
        if not ok:
            return err

    # Manage auth params
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

    params_changed = new_cluster_auth_params != cluster_auth_params

    # Manage users
    if 'users' not in auth_params:
        return ModuleRes(success=True, changed=params_changed)

    users = auth_params['users']
    ok, cluster_users = get_cluster_users(control_instance_admin_api_url, session)
    if not ok:
        return cluster_users

    users_to_add = [
        user for user in users
        if user['username'] in set(u['username'] for u in users) - set(u['username'] for u in cluster_users)
        and not user_is_deleted(user)
    ]

    users_to_edit = [
        user
        for user in users
        if user['username'] in
            set(u['username'] for u in cluster_users)
            & set(u['username'] for u in users if not user_is_deleted(user))
    ]

    users_to_delete = [
        user for user in users
        if user_is_deleted(user)
        and len([u for u in cluster_users if u['username'] == user['username']]) > 0
    ]

    users_changed = False

    for user in users_to_add:
        ok, err = add_cluster_user(control_instance_admin_api_url, session, user)
        if not ok:
            return err

        users_changed = True

    for user in users_to_edit:
        ok, edited_user = edit_cluster_user(control_instance_admin_api_url, session, user)
        if not ok:
            return edited_user

        cluster_user = [u for u in cluster_users if u['username'] == user['username']][0]

        users_changed = cluster_user != edited_user

    for user in users_to_delete:
        ok, err = delete_cluster_user(control_instance_admin_api_url, session, user)
        if not ok:
            return err

        users_changed = True

    return ModuleRes(success=True, changed=params_changed or users_changed)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = manage_auth_params(module.params)

    if res.success == True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
