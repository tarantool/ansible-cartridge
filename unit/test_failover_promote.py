import sys
import unittest

from parameterized import parameterized
import module_utils.helpers as helpers

from unit.instance import Instance

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_failover_promote import failover_promote


def call_failover_promote(console_sock, params):
    return failover_promote({
        'console_sock': console_sock,
        'failover_promote_params': params,
    })


class TestEditTopology(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

        self.instance = Instance()
        self.console_sock = self.instance.console_sock
        self.cookie = self.instance.cluster_cookie

        self.instance.start()

    @parameterized.expand([
        ['disabled'],  # force_inconsistency
        ['eventual'],
    ])
    def test_failover_bad_mode(self, mode):
        self.instance.add_replicaset(
            alias='r1',
            instances=['r1-leader', 'r1-replica', 'r1-replica-2'],
        )

        self.instance.set_failover_params(mode=mode)

        self.instance.set_fail_on('failover_promote')
        self.instance.clear_calls('failover_promote')

        params = {
            'replicaset_leaders': {'r1': 'r1-replica'}
        }

        res = call_failover_promote(
            self.console_sock,
            params
        )
        self.assertTrue(res.failed, msg=res.msg)
        self.assertEqual(res.msg, "Leaders promotion is possible only when stateful failover is enabled")

    def test_failover_promote_fails(self):
        self.instance.add_replicaset(
            alias='r1',
            instances=['r1-leader', 'r1-replica', 'r1-replica-2'],
        )

        self.instance.set_failover_params(mode='stateful', state_provider='stateboard')
        self.instance.set_variable('active_leaders', {
            'r1-uuid': 'r1-leader-uuid',
        })

        self.instance.set_fail_on('failover_promote')
        self.instance.clear_calls('failover_promote')

        params = {
            'replicaset_leaders': {'r1': 'r1-replica'}
        }

        res = call_failover_promote(
            self.console_sock,
            params
        )
        self.assertTrue(res.failed, msg=res.msg)
        self.assertEqual(res.msg, "Failed to promote leaders: cartridge err")

        calls = self.instance.get_calls('failover_promote')
        self.assertEqual(len(calls), 1)

        exp_replicaset_leaders_params = {'r1-uuid': 'r1-replica-uuid'}
        self.assertEqual(calls[0], [exp_replicaset_leaders_params, None])

    def test_replicaset_not_in_cluster(self):
        self.instance.add_replicaset(
            alias='r1',
            instances=['r1-leader', 'r1-replica', 'r1-replica-2'],
        )

        self.instance.set_failover_params(mode='stateful', state_provider='stateboard')
        self.instance.set_variable('active_leaders', {
            'r1-uuid': 'r1-leader-uuid',
        })

        self.instance.clear_calls('failover_promote')

        params = {
            'replicaset_leaders': {'some-bad-rpl': 'r1-replica'}
        }

        res = call_failover_promote(
            self.console_sock,
            params
        )
        self.assertTrue(res.failed, msg=res.msg)
        self.assertEqual(res.msg, "Replicaset 'some-bad-rpl' isn't found in cluster")

    def test_instance_not_in_cluster(self):
        self.instance.add_replicaset(
            alias='r1',
            instances=['r1-leader', 'r1-replica', 'r1-replica-2'],
        )

        self.instance.set_failover_params(mode='stateful', state_provider='stateboard')
        self.instance.set_variable('active_leaders', {
            'r1-uuid': 'r1-leader-uuid',
        })

        self.instance.clear_calls('failover_promote')

        params = {
            'replicaset_leaders': {'r1': 'some-bad-instance'}
        }

        res = call_failover_promote(
            self.console_sock,
            params
        )
        self.assertTrue(res.failed, msg=res.msg)
        self.assertEqual(res.msg, "Instance 'some-bad-instance' isn't found in replicaset 'r1'")

    @parameterized.expand([
        [True],  # force_inconsistency
        [False],
    ])
    def test_failover_promote(self, force_inconsistency):
        self.instance.add_replicaset(
            alias='r1',
            instances=['r1-leader', 'r1-replica', 'r1-replica-2'],
        )

        self.instance.add_replicaset(
            alias='r2',
            instances=['r2-leader', 'r2-replica', 'r2-replica-2'],
        )

        self.instance.add_replicaset(
            alias='r3',
            instances=['r3-leader', 'r3-replica', 'r3-replica-2'],
        )

        self.instance.set_failover_params(mode='stateful', state_provider='stateboard')
        self.instance.set_variable('active_leaders', {
            'r1-uuid': 'r1-leader-uuid',
            'r2-uuid': 'r2-leader-uuid',
            'r3-uuid': 'r3-leader-uuid',
        })

        self.instance.clear_calls('failover_promote')

        params = {
            'replicaset_leaders': {
                'r1': 'r1-replica',
                'r3': 'r3-replica',
            },
        }
        if force_inconsistency:
            params.update({'force_inconsistency': True})

        res = call_failover_promote(
            self.console_sock,
            params
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('failover_promote')
        self.assertEqual(len(calls), 1)

        exp_replicaset_leaders_params = {
            'r1-uuid': 'r1-replica-uuid',
            'r3-uuid': 'r3-replica-uuid',
        }

        exp_force_inconsistency = True if force_inconsistency is True else None
        self.assertEqual(calls[0], [exp_replicaset_leaders_params, exp_force_inconsistency])

    @parameterized.expand([
        [True],  # force_inconsistency
        [False],
    ])
    def test_failover_promote_not_changed(self, force_inconsistency):
        self.instance.add_replicaset(
            alias='r1',
            instances=['r1-leader', 'r1-replica', 'r1-replica-2'],
        )

        self.instance.add_replicaset(
            alias='r2',
            instances=['r2-leader', 'r2-replica', 'r2-replica-2'],
        )

        self.instance.add_replicaset(
            alias='r3',
            instances=['r3-leader', 'r3-replica', 'r3-replica-2'],
        )

        self.instance.set_failover_params(mode='stateful', state_provider='stateboard')
        self.instance.set_variable('active_leaders', {
            'r1-uuid': 'r1-leader-uuid',
            'r2-uuid': 'r2-leader-uuid',
            'r3-uuid': 'r3-leader-uuid',
        })

        self.instance.clear_calls('failover_promote')

        params = {
            'replicaset_leaders': {
                'r1': 'r1-leader',
                'r3': 'r3-leader',
            },
        }
        if force_inconsistency:
            params.update({'force_inconsistency': True})

        res = call_failover_promote(
            self.console_sock,
            params
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('failover_promote')
        self.assertEqual(len(calls), 1)

        exp_replicaset_leaders_params = {
            'r1-uuid': 'r1-leader-uuid',
            'r3-uuid': 'r3-leader-uuid',
        }

        exp_force_inconsistency = True if force_inconsistency is True else None
        self.assertEqual(calls[0], [exp_replicaset_leaders_params, exp_force_inconsistency])

    def tearDown(self):
        self.instance.stop()
        del self.instance
