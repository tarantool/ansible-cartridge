import sys
import unittest

import module_utils.helpers as helpers
from unit.instance import Instance

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_configure_failover import manage_failover


def call_manage_failover_deprecated(console_sock, failover):
    return manage_failover({
        'console_sock': console_sock,
        'failover_params': failover,
    })


class TestFailoverDeprecated(unittest.TestCase):
    def setUp(self):
        self.instance = Instance()
        self.console_sock = self.instance.console_sock
        self.cookie = self.instance.cluster_cookie

        self.instance.start()

    def test_enable_failover_old_cartridge(self):
        self.instance.set_cartridge_version('1.2.0')
        self.instance.bootstrap_cluster()

        # failover disabled
        self.instance.set_failover_params(mode='disabled')
        self.instance.clear_calls('manage_failover')

        res = call_manage_failover_deprecated(self.console_sock, True)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('manage_failover')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], True)

        # eventual failover enabled
        self.instance.set_failover_params(mode='eventual')
        self.instance.clear_calls('manage_failover')

        res = call_manage_failover_deprecated(self.console_sock, True)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('manage_failover')
        self.assertEqual(len(calls), 0)

    def test_disable_failover_old_cartridge(self):
        self.instance.set_cartridge_version('1.2.0')
        self.instance.bootstrap_cluster()

        # failover enabled
        self.instance.set_failover_params(mode='eventual')
        self.instance.clear_calls('manage_failover')

        res = call_manage_failover_deprecated(self.console_sock, False)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('manage_failover')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], False)

        # failover disabled
        self.instance.set_failover_params(mode='disabled')
        self.instance.clear_calls('manage_failover')

        res = call_manage_failover_deprecated(self.console_sock, False)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('manage_failover')
        self.assertEqual(len(calls), 0)

    def test_fail_on_manage_failover_old_cartridge(self):
        self.instance.set_cartridge_version('1.2.0')
        self.instance.bootstrap_cluster()

        # enable failover
        self.instance.set_failover_params(mode='disabled')
        self.instance.clear_calls('manage_failover')
        self.instance.set_fail_on('manage_failover')

        res = call_manage_failover_deprecated(self.console_sock, True)
        self.assertTrue(res.failed)
        self.assertIn('Failed admin_enable_failover', res.msg)
        self.assertIn('cartridge err', res.msg)

        # disable failover
        self.instance.set_failover_params(mode='eventual')
        self.instance.clear_calls('manage_failover')
        self.instance.set_fail_on('manage_failover')

        res = call_manage_failover_deprecated(self.console_sock, False)
        self.assertTrue(res.failed)
        self.assertIn('Failed admin_disable_failover', res.msg)
        self.assertIn('cartridge err', res.msg)

    def test_enable_failover(self):
        self.instance.set_cartridge_version('2.1.0')
        self.instance.bootstrap_cluster()

        # failover disabled
        self.instance.set_failover_params(mode='disabled')
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover_deprecated(self.console_sock, True)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {'mode': 'eventual'})

        # failover enabled
        self.instance.set_failover_params(mode='eventual')
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover_deprecated(self.console_sock, True)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {'mode': 'eventual'})

    def test_disable_failover(self):
        self.instance.set_cartridge_version('2.1.0')
        self.instance.bootstrap_cluster()

        # failover enabled
        self.instance.set_failover_params(mode='eventual')
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover_deprecated(self.console_sock, False)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {'mode': 'disabled'})

        # failover disabled
        self.instance.set_failover_params(mode='disabled')
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover_deprecated(self.console_sock, False)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {'mode': 'disabled'})

    def test_fail_on_manage_failover(self):
        self.instance.set_cartridge_version('2.1.0')
        self.instance.bootstrap_cluster()

        # enable failover
        self.instance.set_failover_params(mode='disabled')
        self.instance.clear_calls('failover_set_params')
        self.instance.set_fail_on('failover_set_params')

        res = call_manage_failover_deprecated(self.console_sock, True)
        self.assertTrue(res.failed)
        self.assertIn('Failed to set failover params', res.msg)
        self.assertIn('cartridge err', res.msg)

        # disable failover
        self.instance.set_failover_params(mode='eventual')
        self.instance.clear_calls('failover_set_params')
        self.instance.set_fail_on('failover_set_params')

        res = call_manage_failover_deprecated(self.console_sock, False)
        self.assertTrue(res.failed)
        self.assertIn('Failed to set failover params', res.msg)
        self.assertIn('cartridge err', res.msg)

    def tearDown(self):
        self.instance.stop()
        del self.instance
