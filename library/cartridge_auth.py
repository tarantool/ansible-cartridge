#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console


argument_spec = {
    'auth': {'required': True, 'type': 'dict'},
    'control_sock': {'required': True, 'type': 'str'},
}


def get_cluster_auth_params(control_console):
    auth_params = control_console.eval('''
        local auth = require('cartridge.auth')
        return auth.get_params()
    ''')
    return True, auth_params


def edit_cluster_auth_params(control_console, enabled=None,
                             cookie_max_age=None, cookie_renew_age=None):
    # Set params
    auth_params_lua = []

    if enabled is not None:
        auth_params_lua.append('enabled = {}'.format('true' if enabled else 'false'))

    if cookie_max_age is not None:
        auth_params_lua.append('cookie_max_age = {}'.format(cookie_max_age))

    if cookie_renew_age is not None:
        auth_params_lua.append('cookie_renew_age = {}'.format(cookie_renew_age))

    res = control_console.eval('''
        local auth = require('cartridge.auth')
        local ok, err = auth.set_params({{
            {}
        }})
        return {{
            ok = ok and true or false,
            err = err and err.err or box.NULL
        }}
    '''.format(
        ', '.join(auth_params_lua)
    ))

    if not res['ok']:
        return False, res['err']

    # Get new params
    ok, new_cluster_auth_params = get_cluster_auth_params(control_console)
    return ok, new_cluster_auth_params


def check_cluster_auth_implements_all(control_console):
    auth_params = control_console.eval('''
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
    res = control_console.eval('''
        local auth = require('cartridge.auth')
        local users, err = auth.list_users()
        return {
            ok = users ~= nil,
            users = users ~= nil and users or err.err
        }
    ''')

    return res['ok'], res['users']


def add_cluster_user(control_console, user):
    add_user_params_lua = [
        '"{}"'.format(user['username']),
    ]
    add_user_params_lua.append('"{}"'.format(user['password']) if 'password' in user else 'nil')
    add_user_params_lua.append('"{}"'.format(user['fullname']) if 'fullname' in user else 'nil')
    add_user_params_lua.append('"{}"'.format(user['email']) if 'email' in user else 'nil')

    res = control_console.eval('''
        local auth = require('cartridge.auth')
        local user, err = auth.add_user({})
        return {{
            ok = user ~= nil,
            err = err and err.err or box.NULL
        }}
    '''.format(', '.join(add_user_params_lua)))

    return res['ok'], res['err']


def delete_cluster_user(control_console, user):
    res = control_console.eval('''
        local auth = require('cartridge.auth')
        local user, err = auth.remove_user('{}')
        return {{
            ok = user ~= nil,
            err = err and err.err or box.NULL
        }}
    '''.format(user['username']))

    return res['ok'], res['err']


def edit_cluster_user(control_console, user):
    edit_user_params_lua = [
        '"{}"'.format(user['username']),
    ]
    edit_user_params_lua.append('"{}"'.format(user['password']) if 'password' in user else 'nil')
    edit_user_params_lua.append('"{}"'.format(user['fullname']) if 'fullname' in user else 'nil')
    edit_user_params_lua.append('"{}"'.format(user['email']) if 'email' in user else 'nil')

    res = control_console.eval('''
        local auth = require('cartridge.auth')
        local user, err = auth.edit_user({})
        return {{
            ok = user ~= nil,
            err = err and err.err or box.NULL
        }}
    '''.format(', '.join(edit_user_params_lua)))

    if not res['ok']:
        return False, res['err']

    # Get user
    res = control_console.eval('''
        local auth = require('cartridge.auth')
        local user, err = auth.get_user('{}')
        return {{
            ok = user ~= nil,
            user = user ~= nil and user or err.err
        }}
    '''.format(user['username']))

    if not res['ok']:
        return False, res['err']

    edited_user = res['user']

    return True, edited_user


def user_is_deleted(user):
    return 'deleted' in user and user['deleted'] is True


def manage_auth(params):
    auth_params = params['auth']
    control_console = get_control_console(params['control_sock'])

    if not auth_params:
        return ModuleRes(success=True, changed=False)

    # Check if auth backeng implements all functions for users managing
    if auth_params.get('users') is not None:
        if not check_cluster_auth_implements_all(control_console):
            errmsg = 'Cluster auth back-end must implement all user managing functions'
            return ModuleRes(success=False, msg=errmsg)

    # Manage auth params
    ok, cluster_auth_params = get_cluster_auth_params(control_console)
    if not ok:
        return ModuleRes(success=False, msg=cluster_auth_params)

    ok, new_cluster_auth_params = edit_cluster_auth_params(
        control_console,
        enabled=auth_params.get('enabled'),
        cookie_max_age=auth_params.get('cookie_max_age'),
        cookie_renew_age=auth_params.get('cookie_renew_age'),
    )
    if not ok:
        return ModuleRes(success=False, msg=new_cluster_auth_params)

    params_changed = new_cluster_auth_params != cluster_auth_params

    # Manage users
    if auth_params.get('users') is None:
        return ModuleRes(success=True, changed=params_changed)

    users = auth_params['users']
    ok, cluster_users = get_cluster_users(control_console)
    if not ok:
        return ModuleRes(success=False, msg=cluster_users)

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
        ok, err = add_cluster_user(control_console, user)
        if not ok:
            return ModuleRes(success=False, msg=err)

        users_changed = True

    for user in users_to_edit:
        cluster_user = [u for u in cluster_users if u['username'] == user['username']][0]

        ok, edited_user = edit_cluster_user(control_console, user)
        if not ok:
            return ModuleRes(success=False, msg=edited_user)

        users_changed = users_changed or cluster_user != edited_user

    for user in users_to_delete:
        ok, err = delete_cluster_user(control_console, user)
        if not ok:
            return ModuleRes(success=False, msg=err)

        users_changed = True

    return ModuleRes(success=True, changed=params_changed or users_changed)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = manage_auth(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
