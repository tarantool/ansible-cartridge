# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest
from instance import Instance

from library.cartridge_manage_failover import manage_failover


def call_manage_failover(console_sock, mode,
                         state_provider=None, stateboard_params=None, etcd2_params=None):
    return manage_failover({
        'console_sock': console_sock,
        'failover_params': {
            'mode': mode,
            'state_provider': state_provider,
            'stateboard_params': stateboard_params,
            'etcd2_params': etcd2_params,
        },
    })


class TestFailover(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_enable_failover_old_cartridge(self):
        self.instance.set_cartridge_version('1.2.0')

        # failover disabled -> enable eventual
        self.instance.set_variable('failover', False)
        self.instance.clear_calls('manage_failover')

        res = call_manage_failover(self.console_sock, mode='eventual')
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('manage_failover')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], 'enable')

        # failover enabled -> enable eventual
        self.instance.set_variable('failover', True)
        self.instance.clear_calls('manage_failover')

        res = call_manage_failover(self.console_sock, mode='eventual')
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('manage_failover')
        self.assertEqual(len(calls), 0)

        # failover disabled -> enable stateful
        self.instance.set_variable('failover', False)
        self.instance.clear_calls('manage_failover')

        res = call_manage_failover(self.console_sock, mode='stateful')
        self.assertFalse(res.success)
        self.assertIn(
            'Stateful failover is supported since cartridge 2',
            res.msg
        )

    def test_disable_failover_old_cartridge(self):
        self.instance.set_cartridge_version('1.2.0')

        # failover enabled -> disable
        self.instance.set_variable('failover', True)
        self.instance.clear_calls('manage_failover')

        res = call_manage_failover(self.console_sock, mode='disabled')
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('manage_failover')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], 'disable')

        # failover disabled -> disable
        self.instance.set_variable('failover', False)
        self.instance.clear_calls('manage_failover')

        res = call_manage_failover(self.console_sock, mode='disabled')
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('manage_failover')
        self.assertEqual(len(calls), 0)

    def test_fail_on_manage_failover_old_cartridge(self):
        self.instance.set_cartridge_version('1.2.0')

        # enable eventual failover
        self.instance.set_variable('failover', False)
        self.instance.clear_calls('manage_failover')
        self.instance.set_fail_on('manage_failover')

        res = call_manage_failover(self.console_sock, mode='eventual')
        self.assertFalse(res.success)
        self.assertIn('Failed admin_enable_failover', res.msg)
        self.assertIn('cartridge err', res.msg)

        # disable failover
        self.instance.set_variable('failover', True)
        self.instance.clear_calls('manage_failover')
        self.instance.set_fail_on('manage_failover')

        res = call_manage_failover(self.console_sock, mode='disabled')
        self.assertFalse(res.success)
        self.assertIn('Failed admin_disable_failover', res.msg)
        self.assertIn('cartridge err', res.msg)

    def test_enable_eventual_failover(self):
        self.instance.set_cartridge_version('2.1.0')

        # failover disabled
        self.instance.set_variable('failover_params', {'mode': 'disabled'})
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover(self.console_sock, mode='eventual')
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {'mode': 'eventual'})

        # failover enabled
        self.instance.set_variable('failover_params', {'mode': 'eventual'})
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover(self.console_sock, mode='eventual')
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {'mode': 'eventual'})

    def test_disable_eventual_failover(self):
        self.instance.set_cartridge_version('2.1.0')

        # failover enabled
        self.instance.set_variable('failover_params', {'mode': 'eventual'})
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover(self.console_sock, mode='disabled')
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {'mode': 'disabled'})

        # failover disabled
        self.instance.set_variable('failover_params', {'mode': 'disabled'})
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover(self.console_sock, mode='disabled')
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {'mode': 'disabled'})

    def test_stateful_failover_with_stateboard(self):
        self.instance.set_cartridge_version('2.1.0')

        STATEBOARD_PARAMS = {
            'uri': 'localhost:3310',
            'password': 'passwd',
        }

        # failover disabled
        self.instance.set_variable('failover_params', {'mode': 'disabled'})
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover(self.console_sock, mode='stateful',
                                   state_provider='stateboard',
                                   stateboard_params=STATEBOARD_PARAMS)
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            'mode': 'stateful',
            'state_provider': 'tarantool',
            'tarantool_params': STATEBOARD_PARAMS,
        })

        # stateful failover enabled - params aren't changed
        self.instance.set_variable('failover_params', {
            'mode': 'stateful',
            'state_provider': 'tarantool',
            'tarantool_params': STATEBOARD_PARAMS,
        })
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover(self.console_sock, mode='stateful',
                                   state_provider='stateboard',
                                   stateboard_params=STATEBOARD_PARAMS)
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            'mode': 'stateful',
            'state_provider': 'tarantool',
            'tarantool_params': STATEBOARD_PARAMS,
        })

        for p in ['uri', 'password']:
            # stateful failover enabled - one param is changed
            self.instance.set_variable('failover_params', {
                'mode': 'stateful',
                'state_provider': 'tarantool',
                'tarantool_params': STATEBOARD_PARAMS,
            })
            self.instance.clear_calls('failover_set_params')

            new_params = STATEBOARD_PARAMS.copy()
            new_params[p] = 'other-string-value'

            res = call_manage_failover(self.console_sock, mode='stateful',
                                       state_provider='stateboard',
                                       stateboard_params=new_params)
            self.assertTrue(res.success, msg=res.msg)
            self.assertTrue(res.changed)

            calls = self.instance.get_calls('failover_set_params')
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], {
                'mode': 'stateful',
                'state_provider': 'tarantool',
                'tarantool_params': new_params,
            })

    def test_stateful_failover_with_etcd2(self):
        self.instance.set_cartridge_version('2.1.0')

        ETCD2_PARAMS = {
            'prefix': '/',
            'lock_delay': 30,
            'username': 'dokshina',
            'password': 'secret',
            'endpoints': ['localhost:2379', 'localhost:2380']
        }

        # failover disabled
        self.instance.set_variable('failover_params', {'mode': 'disabled'})
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover(self.console_sock, mode='stateful',
                                   state_provider='etcd2',
                                   etcd2_params=ETCD2_PARAMS)
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            'mode': 'stateful',
            'state_provider': 'etcd2',
            'etcd2_params': ETCD2_PARAMS,
        })

        # failover disabled
        self.instance.set_variable('failover_params', {'mode': 'disabled'})
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover(self.console_sock, mode='stateful',
                                   state_provider='etcd2',
                                   etcd2_params=None)
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            'mode': 'stateful',
            'state_provider': 'etcd2',
        })

        # stateful failover enabled - params aren't changed
        self.instance.set_variable('failover_params', {
            'mode': 'stateful',
            'state_provider': 'etcd2',
            'etcd2_params': ETCD2_PARAMS,
        })
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover(self.console_sock, mode='stateful',
                                   state_provider='etcd2',
                                   etcd2_params=ETCD2_PARAMS)
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            'mode': 'stateful',
            'state_provider': 'etcd2',
            'etcd2_params': ETCD2_PARAMS,
        })

        for p in ['prefix', 'lock_delay', 'username', 'password', 'endpoints']:
            # stateful failover enabled - one param is changed
            self.instance.set_variable('failover_params', {
                'mode': 'stateful',
                'state_provider': 'etcd2',
                'etcd2_params': ETCD2_PARAMS,
            })
            self.instance.clear_calls('failover_set_params')

            new_params = ETCD2_PARAMS.copy()
            if p in ['prefix', 'username', 'password']:
                new_params[p] = 'other-string-value'
            elif p in ['lock_delay']:
                new_params[p] = new_params[p] + 15
            elif p in ['endpoints']:
                new_params[p].append('localhost:2381')

            res = call_manage_failover(self.console_sock, mode='stateful',
                                       state_provider='etcd2',
                                       etcd2_params=new_params)
            self.assertTrue(res.success, msg=res.msg)
            self.assertTrue(res.changed)

            calls = self.instance.get_calls('failover_set_params')
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], {
                'mode': 'stateful',
                'state_provider': 'etcd2',
                'etcd2_params': new_params,
            })

    def test_stateful_failover_mixed(self):
        self.instance.set_cartridge_version('2.1.0')

        STATEBOARD_PARAMS = {
            'uri': 'localhost:3310',
            'password': 'passwd',
        }

        ETCD2_PARAMS = {
            'prefix': '/',
            'lock_delay': 30,
            'username': 'dokshina',
            'password': 'secret',
            'endpoints': ['localhost:2379', 'localhost:2380']
        }

        # failover disabled -> enable stateboard
        self.instance.set_variable('failover_params', {'mode': 'disabled'})
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover(self.console_sock, mode='stateful',
                                   state_provider='stateboard',
                                   etcd2_params=ETCD2_PARAMS,
                                   stateboard_params=STATEBOARD_PARAMS)
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            'mode': 'stateful',
            'state_provider': 'tarantool',
            'tarantool_params': STATEBOARD_PARAMS,
            'etcd2_params': ETCD2_PARAMS,
        })

        # failover disabled -> enable etcd2
        self.instance.set_variable('failover_params', {'mode': 'disabled'})
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover(self.console_sock, mode='stateful',
                                   state_provider='etcd2',
                                   etcd2_params=ETCD2_PARAMS,
                                   stateboard_params=STATEBOARD_PARAMS)
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            'mode': 'stateful',
            'state_provider': 'etcd2',
            'tarantool_params': STATEBOARD_PARAMS,
            'etcd2_params': ETCD2_PARAMS,
        })

        # stateboard state provider enabled -> switch to etcd2
        self.instance.set_variable('failover_params', {
            'mode': 'stateful',
            'state_provider': 'tarantool',
            'tarantool_params': STATEBOARD_PARAMS,
            'etcd2_params': ETCD2_PARAMS,
        })
        self.instance.clear_calls('failover_set_params')

        res = call_manage_failover(self.console_sock, mode='stateful',
                                   state_provider='etcd2',
                                   etcd2_params=ETCD2_PARAMS,
                                   stateboard_params=STATEBOARD_PARAMS)
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('failover_set_params')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            'mode': 'stateful',
            'state_provider': 'etcd2',
            'tarantool_params': STATEBOARD_PARAMS,
            'etcd2_params': ETCD2_PARAMS,
        })

    def tearDown(self):
        self.instance.stop()
