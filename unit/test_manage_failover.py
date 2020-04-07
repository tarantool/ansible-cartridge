# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest
from instance import Instance

from library.cartridge_manage_failover import manage_failover


def call_manage_failover(control_sock, failover):
    return manage_failover({
        'control_sock': control_sock,
        'failover': failover,
    })


class TestFailover(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_enable_failover(self):
        # failover disabled
        self.instance.set_variable('failover', False)
        self.instance.clear_calls('manage_failover')

        res = call_manage_failover(self.console_sock, True)
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('manage_failover')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], 'enable')

        # failover enabled
        self.instance.set_variable('failover', True)
        self.instance.clear_calls('manage_failover')

        res = call_manage_failover(self.console_sock, True)
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('manage_failover')
        self.assertEqual(len(calls), 0)

    def test_disable_failover(self):
        # failover enabled
        self.instance.set_variable('failover', True)
        self.instance.clear_calls('manage_failover')

        res = call_manage_failover(self.console_sock, False)
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('manage_failover')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], 'disable')

        # failover disabled
        self.instance.set_variable('failover', False)
        self.instance.clear_calls('manage_failover')

        res = call_manage_failover(self.console_sock, False)
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('manage_failover')
        self.assertEqual(len(calls), 0)

    def test_fail_on_manage_failover(self):
        # enable failover
        self.instance.set_variable('failover', False)
        self.instance.clear_calls('manage_failover')
        self.instance.set_fail_on('manage_failover')

        res = call_manage_failover(self.console_sock, True)
        self.assertFalse(res.success)
        self.assertIn('Failed admin_enable_failover', res.msg)
        self.assertIn('cartridge err', res.msg)

        # disable failover
        self.instance.set_variable('failover', True)
        self.instance.clear_calls('manage_failover')
        self.instance.set_fail_on('manage_failover')

        res = call_manage_failover(self.console_sock, False)
        self.assertFalse(res.success)
        self.assertIn('Failed admin_disable_failover', res.msg)
        self.assertIn('cartridge err', res.msg)

    def tearDown(self):
        self.instance.stop()
