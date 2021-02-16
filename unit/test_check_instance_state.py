# Hack ansible.module_utils.helpers import
import sys

import module_utils.helpers as helpers

sys.modules['ansible.module_utils.helpers'] = helpers

import os

sys.path.append(os.path.dirname(__file__))

import unittest
from instance import Instance

from library.cartridge_check_instance_state import check_state


def call_check_instance_state(console_sock, stateboard=False, check_buckets_are_discovered=False):
    return check_state({
        'console_sock': console_sock,
        'stateboard': stateboard,
        'expected_states': ['Unconfigured', 'RolesConfigured'],
        'check_buckets_are_discovered': check_buckets_are_discovered,
    })


def set_confapplier_state(instance, state):
    instance.set_variable('cartridge_confapplier_state', state)


def set_vshard_groups(instance, vshard_groups):
    instance.set_variable('vshard_groups', vshard_groups)


def set_vshard_router_unknown_buckets(instance, groups_unknown_buckets):
    instance.set_variable('unknown_buckets', {
        g[0]: g[1] for g in groups_unknown_buckets.items()
    })


class TestInstanceStarted(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def template_test_instance_not_started(self, stateboard):
        # console sock doesn't exists
        self.instance.remove_file(self.console_sock)
        res = call_check_instance_state(self.console_sock, stateboard)
        self.assertFalse(res.success)
        self.assertIn('Instance socket not found', res.msg)

        # cannot connect to console sock
        bad_socket_path = 'bad-socket-path'
        self.instance.write_file(bad_socket_path)

        res = call_check_instance_state(bad_socket_path, stateboard)
        self.assertFalse(res.success)
        self.assertIn('Failed to connect to socket', res.msg)

    def test_stateboard_not_started(self):
        self.template_test_instance_not_started(stateboard=True)

    def test_stateboard_not_box(self):
        # box.cfg == function

        self.instance.set_box_cfg_function(True)
        res = call_check_instance_state(self.console_sock, stateboard=True)
        self.assertFalse(res.success)
        self.assertIn("Stateboard is not running: box hasn't been configured", res.msg)

    def test_stateboard_not_listen(self):
        # box.cfg.listen == nil

        self.instance.set_box_cfg({})
        res = call_check_instance_state(self.console_sock, stateboard=True)
        self.assertFalse(res.success)
        self.assertIn("Stateboard is not running: box hasn't been configured", res.msg)

    def test_stateboard_started(self):
        # box.cfg.listen ~= nil

        self.instance.set_box_cfg({'listen': 3333})
        res = call_check_instance_state(self.console_sock, stateboard=True)
        self.assertTrue(res.success)

    def test_instance_not_started(self):
        self.template_test_instance_not_started(stateboard=False)

    def test_instance_operation_error(self):
        # require('cartridge.confapplier').get_state() == 'OperationError'

        set_confapplier_state(self.instance, 'OperationError')
        res = call_check_instance_state(self.console_sock)
        self.assertFalse(res.success)
        self.assertIn("Instance is not in one of states: ['Unconfigured', 'RolesConfigured'], "
                      "it's in 'OperationError' state", res.msg)

    def test_instance_not_bootstrapped(self):
        # groups not bootstrapped

        set_confapplier_state(self.instance, 'RolesConfigured')
        set_vshard_router_unknown_buckets(self.instance, {'hot': 1000, 'cold': 1000})

        set_vshard_groups(self.instance, {
            'hot': {'bucket_count': 2000, 'bootstrapped': False},
            'cold': {'bucket_count': 30000, 'bootstrapped': False},
        })
        res = call_check_instance_state(self.console_sock, check_buckets_are_discovered=True)
        self.assertTrue(res.success)

        set_vshard_groups(self.instance, {
            'hot': {'bucket_count': 2000, 'bootstrapped': True},
            'cold': {'bucket_count': 30000, 'bootstrapped': False},
        })
        res = call_check_instance_state(self.console_sock, check_buckets_are_discovered=True)
        self.assertFalse(res.success)
        self.assertIn("1000 out of 2000 buckets are not discovered in group 'hot'", res.msg)

        set_vshard_groups(self.instance, {
            'hot': {'bucket_count': 2000, 'bootstrapped': False},
            'cold': {'bucket_count': 30000, 'bootstrapped': True},
        })
        res = call_check_instance_state(self.console_sock, check_buckets_are_discovered=True)
        self.assertFalse(res.success)
        self.assertIn("1000 out of 30000 buckets are not discovered in group 'cold'", res.msg)

    def test_instance_no_router(self):
        # vshard_router.get(group_name) == nil

        set_confapplier_state(self.instance, 'RolesConfigured')
        set_vshard_groups(self.instance, {
            'hot': {'bucket_count': 2000, 'bootstrapped': True},
            'cold': {'bucket_count': 30000, 'bootstrapped': True},
        })

        set_vshard_router_unknown_buckets(self.instance, {'hot': 1000})
        res = call_check_instance_state(self.console_sock, check_buckets_are_discovered=True)
        self.assertFalse(res.success)
        self.assertIn("1000 out of 2000 buckets are not discovered in group 'hot'", res.msg)

        set_vshard_router_unknown_buckets(self.instance, {'cold': 1000})
        res = call_check_instance_state(self.console_sock, check_buckets_are_discovered=True)
        self.assertFalse(res.success)
        self.assertIn("1000 out of 30000 buckets are not discovered in group 'cold'", res.msg)

    def test_instance_discovering(self):
        # unknown_buckets > 0

        set_confapplier_state(self.instance, 'RolesConfigured')
        set_vshard_groups(self.instance, {
            'hot': {'bucket_count': 2000, 'bootstrapped': True},
            'cold': {'bucket_count': 30000, 'bootstrapped': True},
        })

        set_vshard_router_unknown_buckets(self.instance, {'hot': 1000, 'cold': 0})
        res = call_check_instance_state(self.console_sock, check_buckets_are_discovered=True)
        self.assertFalse(res.success)
        self.assertIn("1000 out of 2000 buckets are not discovered in group 'hot'", res.msg)

        set_vshard_router_unknown_buckets(self.instance, {'hot': 0, 'cold': 1000})
        res = call_check_instance_state(self.console_sock, check_buckets_are_discovered=True)
        self.assertFalse(res.success)
        self.assertIn("1000 out of 30000 buckets are not discovered in group 'cold'", res.msg)

    def test_instance_bootstrapped(self):
        set_confapplier_state(self.instance, 'RolesConfigured')
        set_vshard_groups(self.instance, {
            'hot': {'bucket_count': 2000, 'bootstrapped': True},
            'cold': {'bucket_count': 30000, 'bootstrapped': True},
        })
        set_vshard_router_unknown_buckets(self.instance, {'cold': 0, 'hot': 0})
        res = call_check_instance_state(self.console_sock, check_buckets_are_discovered=True)
        self.assertTrue(res.success)

    def tearDown(self):
        self.instance.stop()
