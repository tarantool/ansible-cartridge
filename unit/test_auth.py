# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest
from instance import Instance

from library.cartridge_auth import manage_auth


def call_manage_auth(control_sock, enabled=None, cookie_max_age=None,
                     cookie_renew_age=None, users=None):
    return manage_auth({
        'control_sock': control_sock,
        'auth': {
            'enabled': enabled,
            'cookie_max_age': cookie_max_age,
            'cookie_renew_age': cookie_renew_age,
            'users': users,
        }
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
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_empty(self):
        res = call_manage_auth(self.console_sock)
        self.assertTrue(res.success, msg=res.msg)
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

        self.instance.set_variable('auth_params', current_auth)

        for p in ['enabled', 'cookie_max_age', 'cookie_renew_age']:
            # call with current value (res.changed is False)
            auth_patch = {p: current_auth[p]}

            self.instance.clear_calls('auth_set_params')

            res = call_manage_auth(self.console_sock, **auth_patch)
            self.assertTrue(res.success, msg=res.msg)
            self.assertFalse(res.changed)

            calls = self.instance.get_calls('auth_set_params')
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], auth_patch)

            # call with a new value (res.changed is True)
            auth_patch = {p: new_values[p]}

            self.instance.clear_calls('auth_set_params')

            res = call_manage_auth(self.console_sock, **auth_patch)
            self.assertTrue(res.success, msg=res.msg)
            self.assertTrue(res.changed)

            calls = self.instance.get_calls('auth_set_params')
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], auth_patch)

        # fail on auth_set_params
        self.instance.set_fail_on('auth_set_params')
        self.instance.set_variable('auth_params', {})

        res = call_manage_auth(self.console_sock, enabled=True)
        self.assertFalse(res.success)
        self.assertIn('cartridge err', res.msg)

    def test_user_functions_implemented(self):
        USER = {
            'username': 'dokshina',
            'password': 'iloverandompasswords',
        }

        # no one operation is implemented
        self.instance.set_variable('webui_auth_params', {})
        res = call_manage_auth(self.console_sock, users=[USER])
        self.assertFalse(res.success)
        self.assertIn('back-end must implement all user managing functions', res.msg)

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
            self.assertFalse(res.success)
            self.assertIn('back-end must implement all user managing functions', res.msg)

    def test_add_user(self):
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

        # add a new user
        self.instance.set_variable('users', [USER1])
        self.instance.clear_calls('auth_add_user')
        self.instance.clear_calls('auth_edit_user')
        self.instance.clear_calls('auth_remove_user')

        res = call_manage_auth(self.console_sock, users=[USER1, USER2])
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('auth_add_user')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], USER2)

        calls = self.instance.get_calls('auth_edit_user')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], USER1)

        calls = self.instance.get_calls('auth_remove_user')
        self.assertEqual(len(calls), 0)

        # add existed user
        self.instance.set_variable('users', [USER1, USER2])
        self.instance.clear_calls('auth_add_user')
        self.instance.clear_calls('auth_edit_user')
        self.instance.clear_calls('auth_remove_user')

        res = call_manage_auth(self.console_sock, users=[USER1, USER2])
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('auth_add_user')
        self.assertEqual(len(calls), 0)

        calls = self.instance.get_calls('auth_edit_user')
        self.assertEqual(len(calls), 2)
        self.assertIn(USER1, calls)
        self.assertIn(USER2, calls)

        calls = self.instance.get_calls('auth_remove_user')
        self.assertEqual(len(calls), 0)

        # fail on auth_add_user
        self.instance.set_fail_on('auth_add_user')
        self.instance.set_variable('users', [])

        res = call_manage_auth(self.console_sock, users=[USER1])
        self.assertFalse(res.success)
        self.assertIn('cartridge err', res.msg)

    def test_edit_user(self):
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
            self.instance.set_variable('users', [USER])

            self.instance.clear_calls('auth_add_user')
            self.instance.clear_calls('auth_edit_user')
            self.instance.clear_calls('auth_remove_user')

            user_patch = {
                'username': USER['username'],
                param: value,
            }

            res = call_manage_auth(self.console_sock, users=[user_patch])
            self.assertTrue(res.success, msg=res.msg)
            if param != 'password':
                self.assertTrue(res.changed)
            else:
                self.assertFalse(res.changed)

            calls = self.instance.get_calls('auth_add_user')
            self.assertEqual(len(calls), 0)

            calls = self.instance.get_calls('auth_edit_user')
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], user_patch)

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
        self.assertFalse(res.success)
        self.assertIn('cartridge err', res.msg)

    def test_delete_user(self):
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
        self.instance.set_variable('users', [USER1, USER2])
        self.instance.clear_calls('auth_add_user')
        self.instance.clear_calls('auth_edit_user')
        self.instance.clear_calls('auth_remove_user')

        deleted_user2 = USER2.copy()
        deleted_user2['deleted'] = True

        res = call_manage_auth(self.console_sock, users=[USER1, deleted_user2])
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('auth_add_user')
        self.assertEqual(len(calls), 0)

        calls = self.instance.get_calls('auth_edit_user')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], USER1)

        calls = self.instance.get_calls('auth_remove_user')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], USER2['username'])

        # delete non-existed user
        self.instance.set_variable('users', [USER1])
        self.instance.clear_calls('auth_add_user')
        self.instance.clear_calls('auth_edit_user')
        self.instance.clear_calls('auth_remove_user')

        deleted_user2 = USER2.copy()
        deleted_user2['deleted'] = True

        res = call_manage_auth(self.console_sock, users=[USER1, deleted_user2])
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('auth_add_user')
        self.assertEqual(len(calls), 0)

        calls = self.instance.get_calls('auth_edit_user')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], USER1)

        calls = self.instance.get_calls('auth_remove_user')
        self.assertEqual(len(calls), 0)

        # fail on auth_remove_user
        self.instance.set_fail_on('auth_remove_user')
        self.instance.set_variable('users', [USER1])

        deleted_user1 = USER1.copy()
        deleted_user1['deleted'] = True

        res = call_manage_auth(self.console_sock, users=[deleted_user1])
        self.assertFalse(res.success)
        self.assertIn('cartridge err', res.msg)

    def test_empty_users(self):
        # all required operations are implemented
        set_user_functions_implemented(self.instance)

        USER = {
            'username': 'dokshina',
            'email': 'dokshina@tarantool.love',
            'fullname': 'Elizaveta Dokshina',
        }

        # delete existed user
        self.instance.set_variable('users', [USER])
        self.instance.clear_calls('auth_add_user')
        self.instance.clear_calls('auth_edit_user')
        self.instance.clear_calls('auth_remove_user')

        res = call_manage_auth(self.console_sock, users=[])
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('auth_add_user')
        self.assertEqual(len(calls), 0)

        calls = self.instance.get_calls('auth_edit_user')
        self.assertEqual(len(calls), 0)

        calls = self.instance.get_calls('auth_remove_user')
        self.assertEqual(len(calls), 0)

    def tearDown(self):
        self.instance.stop()
