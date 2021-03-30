#!/usr/bin/python

from ansible.module_utils.helpers import execute_module, ModuleRes
from ansible.module_utils.helpers import get_control_console
from ansible.module_utils.helpers import filter_none_values

argument_spec = {
    'auth': {'required': True, 'type': 'dict'},
    'console_sock': {'required': True, 'type': 'str'},
}


def get_cluster_auth_params(control_console):
    auth_params, _ = control_console.eval_res_err('''
        local auth = require('cartridge.auth')
        return auth.get_params()
    ''')
    return auth_params


def edit_cluster_auth_params(control_console, auth_params):
    # Set params

    func_body = '''
        local auth = require('cartridge.auth')
        local auth_params = ...
        return auth.set_params(auth_params)
    '''
    ok, err = control_console.eval_res_err(func_body, filter_none_values(auth_params))

    if not ok:
        return None, err

    # Get new params
    new_cluster_auth_params = get_cluster_auth_params(control_console)
    return new_cluster_auth_params, None


def check_cluster_auth_implements_all(control_console):
    auth_params, _ = control_console.eval_res_err('''
        local auth = require('cartridge.webui.api-auth')
        return auth.get_auth_params()
    ''')

    required_operations = [
        'implements_list_users', 'implements_remove_user',
        'implements_add_user', 'implements_edit_user',
        'implements_get_user', 'implements_check_password',
    ]

    return all([op in auth_params and auth_params[op] is True for op in required_operations])


def get_cluster_users(control_console):
    users, err = control_console.eval_res_err('''
        local auth = require('cartridge.auth')
        return auth.list_users()
    ''')

    return users, err


def add_cluster_user(control_console, user):
    func_body = '''
        local auth = require('cartridge.auth')
        local user = ...

        for param_name in pairs(user) do
            if user[param_name] == nil then
                user[param_name] = nil
            end
        end

        return auth.add_user(user.username, user.password, user.fullname, user.email)
    '''

    user, err = control_console.eval_res_err(func_body, user)

    return user, err


def delete_cluster_user(control_console, user):
    func_body = '''
        local auth = require('cartridge.auth')
        local username = ...
        return auth.remove_user(username)
    '''

    user, err = control_console.eval_res_err(func_body, user['username'])
    return user, err


def edit_cluster_user(control_console, user):
    func_body = '''
        local auth = require('cartridge.auth')
        local user = ...

        for param_name in pairs(user) do
            if user[param_name] == nil then
                user[param_name] = nil
            end
        end

        return auth.edit_user(user.username, user.password, user.fullname, user.email)
    '''
    user, err = control_console.eval_res_err(func_body, user)

    if err is not None:
        return None, err

    # Get user
    func_body = '''
        local auth = require('cartridge.auth')
        local username = ...
        return auth.get_user(username)
    '''
    user, err = control_console.eval_res_err(
        func_body, user['username']
    )

    if err is not None:
        return None, err

    return user, None


def user_is_deleted(user):
    return 'deleted' in user and user['deleted'] is True


def users_are_equal(user1, user2):
    for key in user1:
        if key == 'version':
            continue

        if key not in user2:
            return False

        if user1[key] != user2[key]:
            return False

    for key in user2:
        if key == 'version':
            continue

        if key not in user1:
            return False

    return True


def manage_auth(params):
    auth_params = params['auth']
    control_console = get_control_console(params['console_sock'])

    if not auth_params:
        return ModuleRes(changed=False)

    # Check if auth backend implements all functions for users management
    if auth_params.get('users') is not None:
        if not check_cluster_auth_implements_all(control_console):
            errmsg = 'Cluster auth backend must implement all user management functions'
            return ModuleRes(failed=True, msg=errmsg)

    # Manage auth params
    common_auth_params = auth_params.copy()
    if 'users' in common_auth_params:
        del common_auth_params['users']

    current_auth_params = get_cluster_auth_params(control_console)

    new_cluster_auth_params, err = edit_cluster_auth_params(
        control_console,
        common_auth_params,
    )
    if err is not None:
        return ModuleRes(failed=True, msg=err)

    params_changed = new_cluster_auth_params != current_auth_params

    # Manage users
    if auth_params.get('users') is None:
        return ModuleRes(changed=params_changed)

    users = auth_params['users']
    cluster_users, err = get_cluster_users(control_console)
    if err is not None:
        return ModuleRes(failed=True, msg=err)

    # find new users
    new_usernames = set(u['username'] for u in users).difference(
        set(u['username'] for u in cluster_users)
    )

    users_to_add = list(filter(
        lambda u: u['username'] in new_usernames and not user_is_deleted(u),
        users
    ))

    # find users to edit
    users_to_edit = list(filter(
        lambda u: u['username'] not in new_usernames and not user_is_deleted(u),
        users
    ))

    # find users to delete
    users_to_delete = list(filter(
        lambda u: user_is_deleted(u) and len(list(filter(
            lambda c: c['username'] == u['username'],
            cluster_users)
        )) > 0,
        users
    ))

    users_changed = False

    for user in users_to_add:
        _, err = add_cluster_user(control_console, user)
        if err is not None:
            return ModuleRes(failed=True, msg=err)

        users_changed = True

    for user in users_to_edit:
        cluster_user = [u for u in cluster_users if u['username'] == user['username']][0]

        edited_user, err = edit_cluster_user(control_console, user)
        if err is not None:
            return ModuleRes(failed=True, msg=err)

        users_changed = users_changed or not users_are_equal(cluster_user, edited_user)

    for user in users_to_delete:
        _, err = delete_cluster_user(control_console, user)
        if err is not None:
            return ModuleRes(failed=True, msg=err)

        users_changed = True

    return ModuleRes(changed=params_changed or users_changed)


if __name__ == '__main__':
    execute_module(argument_spec, manage_auth)
