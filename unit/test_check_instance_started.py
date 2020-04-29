# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest
from instance import Instance

from library.cartridge_check_instance_started import check_instance_started


def call_check_instance_started(control_sock, stateboard=False):
    return check_instance_started({
        'control_sock': control_sock,
        'stateboard': stateboard,
    })


def set_myself(instance, status):
    instance.set_variable('membership_myself', {
        'status': status
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
        res = call_check_instance_started(self.console_sock, stateboard)
        self.assertFalse(res.success)
        self.assertIn('Instance socket not found', res.msg)

        # cannot connect to console sock
        bad_socket_path = 'bad-socket-path'
        self.instance.write_file(bad_socket_path)

        res = call_check_instance_started(bad_socket_path, stateboard)

        self.assertFalse(res.success)
        self.assertIn('Failed to connect to socket', res.msg)

    def test_instance_not_started(self):
        self.template_test_instance_not_started(stateboard=False)

    def test_stateboard_not_started(self):
        self.template_test_instance_not_started(stateboard=True)

    def test_alive(self):
        # not stateboard
        # require('membership').myself().status is 'active'
        set_myself(self.instance, status='alive')
        self.instance.clear_calls('membership_myself')
        res = call_check_instance_started(self.console_sock)
        self.assertTrue(res.success, msg=res.msg)

        calls = self.instance.get_calls('membership_myself')
        self.assertEqual(len(calls), 1)

        # stateboard
        set_myself(self.instance, status='alive')
        self.instance.clear_calls('membership_myself')
        res = call_check_instance_started(self.console_sock, stateboard=True)
        self.assertTrue(res.success, msg=res.msg)

        calls = self.instance.get_calls('membership_myself')
        self.assertEqual(len(calls), 0)

    def test_dead(self):
        # not stateboard
        # require('membership').myself().status is 'dead'
        set_myself(self.instance, status='dead')
        self.instance.clear_calls('membership_myself')
        res = call_check_instance_started(self.console_sock)
        self.assertFalse(res.success)

    def tearDown(self):
        self.instance.stop()
