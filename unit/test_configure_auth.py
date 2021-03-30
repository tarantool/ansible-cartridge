import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import unittest

from unit.instance import Instance
from library.cartridge_configure_auth import manage_auth


def remove_trailing_nones(specified_list):
    while specified_list[-1] is None:
        specified_list.pop()

    return specified_list


def call_manage_auth(console_sock, enabled=None, cookie_max_age=None,
                     cookie_renew_age=None, users=None):
    auth = {}
    if enabled is not None:
        auth['enabled'] = enabled
    if cookie_max_age is not None:
        auth['cookie_max_age'] = cookie_max_age
    if cookie_renew_age is not None:
        auth['cookie_renew_age'] = cookie_renew_age
    if users is not None:
        auth['users'] = users
    return manage_auth({
        'console_sock': console_sock,
        'auth': auth,
    })


def set_user_functions_implemented(instance):
    required_operations = [
        'implements_list_users', 'implements_remove_user',
        'implements_add_user', 'implements_edit_user',
        'implements_get_user', 'implements_check_password',
    ]
    instance.set_variable('webui_auth_params', {
        op: True for op in required_operations
    })


class TestAuth(unittest.TestCase):
    def setUp(self):
        self.instance = Instance()
        self.console_sock = self.instance.console_sock
        self.cookie = self.instance.cluster_cookie

        self.instance.start()

    def test_empty(self):
        self.instance.bootstrap_cluster()

        res = call_manage_auth(self.console_sock)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

    def test_edit_params(self):
        current_auth = {
            'enabled': False,
            'cookie_max_age': 100,
            'cookie_renew_age': 10,
        }

        new_values = {
            'enabled': True,
            'cookie_max_age': 200,
            'cookie_renew_age': 20,
        }

        self.instance.bootstrap_cluster()
        self.instance.set_auth(current_auth)

        for p in ['enabled', 'cookie_max_age', 'cookie_renew_age']:
            # call with current value (res.changed is False)
            auth_patch = {p: current_auth[p]}

            self.instance.clear_calls('auth_set_params')

            res = call_manage_auth(self.console_sock, **auth_patch)
            self.assertFalse(res.failed, msg=res.msg)
            self.assertFalse(res.changed)

            calls = self.instance.get_calls('auth_set_params')
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], auth_patch)

            # call with a new value (res.changed is True)
            auth_patch = {p: new_values[p]}

            self.instance.clear_calls('auth_set_params')

            res = call_manage_auth(self.console_sock, **auth_patch)
            self.assertFalse(res.failed, msg=res.msg)
            self.assertTrue(res.changed)

            calls = self.instance.get_calls('auth_set_params')
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], auth_patch)

        # fail on auth_set_params
        self.instance.set_fail_on('auth_set_params')

        res = call_manage_auth(self.console_sock, enabled=True)
        self.assertTrue(res.failed)
        self.assertIn('cartridge err', res.msg)

    def test_user_functions_implemented(self):
        USER = {
            'username': 'dokshina',
            'password': 'iloverandompasswords',
        }

        self.instance.bootstrap_cluster()

        # no one operation is implemented
        self.instance.set_variable('webui_auth_params', {})
        res = call_manage_auth(self.console_sock, users=[USER])
        self.assertTrue(res.failed)
        self.assertIn('backend must implement all user management functions', res.msg)

        # check that all operations are required
        required_operations = [
            'implements_list_users', 'implements_remove_user',
            'implements_add_user', 'implements_edit_user',
            'implements_get_user', 'implements_check_password',
        ]
        for missed_op in required_operations:
            self.instance.set_variable('webui_auth_params', {
                op: True for op in required_operations if op != missed_op
            })

            res = call_manage_auth(self.console_sock, users=[USER])
            self.assertTrue(res.failed)
            self.assertIn('backend must implement all user management functions', res.msg)

    def test_add_user(self):
        self.instance.bootstrap_cluster()

        # all required operations are implemented
        set_user_functions_implemented(self.instance)

        USER1 = {
            'username': 'dokshina',
            'password': 'qwerty',
            'email': 'dokshina@tarantool.love',
            'fullname': 'Elizaveta Dokshina',
        }
        USER2 = {
            'username': 'elizabeth',
            'password': 'qwerty',
            'email': 'dokshina@tarantool.hate',
            'fullname': 'The Princess',
        }
        USER3 = {
            'username': 'marina',
            'password': 'qwerty',
        }

        # add a new user
        self.instance.set_users([USER1])
        self.instance.clear_calls('auth_add_user')
        self.instance.clear_calls('auth_edit_user')
        self.instance.clear_calls('auth_remove_user')

        res = call_manage_auth(self.console_sock, users=[USER1, USER2])
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('auth_add_user')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], [
            USER2.get(p) for p in ['username', 'password', 'fullname', 'email']
        ])

        calls = self.instance.get_calls('auth_edit_user')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], [
            USER1.get(p) for p in ['username', 'password', 'fullname', 'email']
        ])

        calls = self.instance.get_calls('auth_remove_user')
        self.assertEqual(len(calls), 0)

        # add existed user
        self.instance.set_users([USER1, USER2])
        self.instance.clear_calls('auth_add_user')
        self.instance.clear_calls('auth_edit_user')
        self.instance.clear_calls('auth_remove_user')

        res = call_manage_auth(self.console_sock, users=[USER1, USER2])
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('auth_add_user')
        self.assertEqual(len(calls), 0)

        calls = self.instance.get_calls('auth_edit_user')
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], [
            USER1.get(p) for p in ['username', 'password', 'fullname', 'email']
        ])
        self.assertEqual(calls[1], [
            USER2.get(p) for p in ['username', 'password', 'fullname', 'email']
        ])

        calls = self.instance.get_calls('auth_remove_user')
        self.assertEqual(len(calls), 0)

        # fail on auth_add_user
        self.instance.set_fail_on('auth_add_user')
        self.instance.set_users([])

        res = call_manage_auth(self.console_sock, users=[USER1, USER2, USER3])
        self.assertTrue(res.failed)
        self.assertIn('cartridge err', res.msg)

    def test_edit_user(self):
        self.instance.bootstrap_cluster()

        # all required operations are implemented
        set_user_functions_implemented(self.instance)

        USER = {
            'username': 'dokshina',
            'email': 'dokshina@tarantool.love',
            'fullname': 'Elizaveta Dokshina',
        }

        new_params = {
            'password': 'new-password',
            'email': 'dokshina@tarantool.hate',
            'fullname': 'The Princess',
        }

        for param, value in new_params.items():
            self.instance.set_users([USER])

            self.instance.clear_calls('auth_add_user')
            self.instance.clear_calls('auth_edit_user')
            self.instance.clear_calls('auth_remove_user')

            user_patch = {
                'username': USER['username'],
                param: value,
            }

            res = call_manage_auth(self.console_sock, users=[user_patch])
            self.assertFalse(res.failed, msg=res.msg)
            if param != 'password':
                self.assertTrue(res.changed)
            else:
                self.assertFalse(res.changed)

            calls = self.instance.get_calls('auth_add_user')
            self.assertEqual(len(calls), 0)

            calls = self.instance.get_calls('auth_edit_user')
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], remove_trailing_nones([
                user_patch.get(p) for p in ['username', 'password', 'fullname', 'email']
            ]))

            calls = self.instance.get_calls('auth_remove_user')
            self.assertEqual(len(calls), 0)

        # fail on auth_edit_user
        self.instance.set_fail_on('auth_edit_user')
        self.instance.set_variable('users', [USER])

        user_patch = {
            'username': USER['username'],
            'password': 'new-password',
        }

        res = call_manage_auth(self.console_sock, users=[user_patch])
        self.assertTrue(res.failed)
        self.assertIn('cartridge err', res.msg)

    def test_edit_user_no_version(self):
        self.instance.bootstrap_cluster()

        # all required operations are implemented
        set_user_functions_implemented(self.instance)
        self.instance.set_variable('user_has_version', False)

        USER = {
            'username': 'dokshina',
            'email': 'dokshina@tarantool.love',
            'fullname': 'Elizaveta Dokshina',
        }

        new_params = {
            'password': 'new-password',
            'email': 'dokshina@tarantool.love_a_bit_more',
            'fullname': 'The Princess',
        }

        for param, value in new_params.items():
            self.instance.set_users([USER])

            self.instance.clear_calls('auth_add_user')
            self.instance.clear_calls('auth_edit_user')
            self.instance.clear_calls('auth_remove_user')

            user_patch = {
                'username': USER['username'],
                param: value,
            }

            res = call_manage_auth(self.console_sock, users=[user_patch])
            self.assertFalse(res.failed, msg=res.msg)
            if param != 'password':
                self.assertTrue(res.changed)
            else:
                self.assertFalse(res.changed)

            calls = self.instance.get_calls('auth_add_user')
            self.assertEqual(len(calls), 0)

            calls = self.instance.get_calls('auth_edit_user')
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], remove_trailing_nones([
                user_patch.get(p) for p in ['username', 'password', 'fullname', 'email']
            ]))

            calls = self.instance.get_calls('auth_remove_user')
            self.assertEqual(len(calls), 0)

        # fail on auth_edit_user
        self.instance.set_fail_on('auth_edit_user')
        self.instance.set_users([USER])

        user_patch = {
            'username': USER['username'],
            'password': 'new-password',
        }

        res = call_manage_auth(self.console_sock, users=[user_patch])
        self.assertTrue(res.failed)
        self.assertIn('cartridge err', res.msg)

    def test_delete_user(self):
        self.instance.bootstrap_cluster()

        # all required operations are implemented
        set_user_functions_implemented(self.instance)

        USER1 = {
            'username': 'dokshina',
            'email': 'dokshina@tarantool.love',
            'fullname': 'Elizaveta Dokshina',
        }
        USER2 = {
            'username': 'elizabeth',
            'email': 'dokshina@tarantool.hate',
            'fullname': 'The Princess',
        }

        # delete existed user
        self.instance.set_users([USER1, USER2])
        self.instance.clear_calls('auth_add_user')
        self.instance.clear_calls('auth_edit_user')
        self.instance.clear_calls('auth_remove_user')

        deleted_user2 = USER2.copy()
        deleted_user2['deleted'] = True

        res = call_manage_auth(self.console_sock, users=[USER1, deleted_user2])
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('auth_add_user')
        self.assertEqual(len(calls), 0)

        calls = self.instance.get_calls('auth_edit_user')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], [
            USER1.get(p) for p in ['username', 'password', 'fullname', 'email']
        ])

        calls = self.instance.get_calls('auth_remove_user')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], USER2['username'])

        # delete non-existed user
        self.instance.set_users([USER1])
        self.instance.clear_calls('auth_add_user')
        self.instance.clear_calls('auth_edit_user')
        self.instance.clear_calls('auth_remove_user')

        deleted_user2 = USER2.copy()
        deleted_user2['deleted'] = True

        res = call_manage_auth(self.console_sock, users=[USER1, deleted_user2])
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('auth_add_user')
        self.assertEqual(len(calls), 0)

        calls = self.instance.get_calls('auth_edit_user')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], [
            USER1.get(p) for p in ['username', 'password', 'fullname', 'email']
        ])

        calls = self.instance.get_calls('auth_remove_user')
        self.assertEqual(len(calls), 0)

        # fail on auth_remove_user
        self.instance.set_fail_on('auth_remove_user')
        self.instance.set_users([USER1])

        deleted_user1 = USER1.copy()
        deleted_user1['deleted'] = True

        res = call_manage_auth(self.console_sock, users=[deleted_user1])
        self.assertTrue(res.failed)
        self.assertIn('cartridge err', res.msg)

    def test_empty_users(self):
        self.instance.bootstrap_cluster()

        # all required operations are implemented
        set_user_functions_implemented(self.instance)

        USER = {
            'username': 'dokshina',
            'email': 'dokshina@tarantool.love',
            'fullname': 'Elizaveta Dokshina',
        }

        # delete existed user
        self.instance.set_users([USER])
        self.instance.clear_calls('auth_add_user')
        self.instance.clear_calls('auth_edit_user')
        self.instance.clear_calls('auth_remove_user')

        res = call_manage_auth(self.console_sock, users=[])
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('auth_add_user')
        self.assertEqual(len(calls), 0)

        calls = self.instance.get_calls('auth_edit_user')
        self.assertEqual(len(calls), 0)

        calls = self.instance.get_calls('auth_remove_user')
        self.assertEqual(len(calls), 0)

    def tearDown(self):
        self.instance.stop()
        del self.instance
