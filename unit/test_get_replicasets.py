# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest

from library.cartridge_get_replicasets import get_replicasets


def call_get_replicasets(hostvars, control_host='', play_hosts=None):
    if play_hosts is None:
        play_hosts = hostvars.keys()

    return get_replicasets({
        'control_host': control_host,
        'hostvars': hostvars,
        'play_hosts': play_hosts,
    })


class TestGetReplicasets(unittest.TestCase):
    def test_empty_replicasets(self):
        res = call_get_replicasets({
            'instance-1': {
                'config': {
                    'advertise_uri': 'localhost:3301',
                }
            }
        })
        self.assertTrue(res.success, msg=res.msg)
        self.assertEqual(res.meta, {
            'replicasets': [],
            'join_host': '',
        })

    def test_without_failover_priority(self):
        # one-instance
        res = call_get_replicasets({
            'instance-1': {
                'replicaset_alias': 'replicaset-1',
            }
        })
        self.assertTrue(res.success, msg=res.msg)

        self.assertIn('replicasets', res.meta)
        self.assertIn('join_host', res.meta)

        self.assertEqual(res.meta['join_host'], 'instance-1')

        self.assertEqual(len(res.meta['replicasets']), 1)
        replicaset = res.meta['replicasets'][0]

        self.assertIn('failover_priority', replicaset)
        self.assertEqual(len(replicaset['failover_priority']), 1)
        self.assertEqual(replicaset['failover_priority'][0], 'instance-1')

        # multi-instance
        replicaset_vars = {
            'replicaset_alias': 'replicaset-1',
        }

        res = call_get_replicasets({
            'instance-1': replicaset_vars,
            'instance-2': replicaset_vars,
        })
        self.assertTrue(res.success, msg=res.msg)

        self.assertIn('replicasets', res.meta)
        self.assertIn('join_host', res.meta)

        self.assertEqual(len(res.meta['replicasets']), 1)
        replicaset = res.meta['replicasets'][0]

        self.assertIn('failover_priority', replicaset)
        self.assertEqual(len(replicaset['failover_priority']), 1)
        self.assertIn(replicaset['failover_priority'][0], ['instance-1', 'instance-2'])
        self.assertEqual(res.meta['join_host'], replicaset['failover_priority'][0])

    def test_failover_priority_specified(self):
        replicaset_vars = {
            'replicaset_alias': 'replicaset-1',
            'failover_priority': ['r1-leader', 'r1-replica']
        }

        res = call_get_replicasets({
            'r1-leader': replicaset_vars,
            'r1-replica': replicaset_vars,
        })
        self.assertTrue(res.success, msg=res.msg)

        self.assertIn('replicasets', res.meta)
        self.assertIn('join_host', res.meta)

        self.assertEqual(len(res.meta['replicasets']), 1)
        replicaset = res.meta['replicasets'][0]

        self.assertIn('failover_priority', replicaset)
        self.assertEqual(len(replicaset['failover_priority']), 2)
        self.assertEqual(replicaset['failover_priority'], replicaset_vars['failover_priority'])
        self.assertEqual(res.meta['join_host'], replicaset['failover_priority'][0])

    def test_two_replicasets(self):
        replicasets = [
            {
                'vars': {
                    'replicaset_alias': 'replicaset-1',
                    'roles': ['role-1'],
                    'failover_priority': ['r1-leader', 'r1-replica'],
                    'all_rw': True,
                    'weight': 1,
                    'vshard_group': 'group-1'
                },
                'instances': ['r1-leader', 'r1-replica'],
            },
            {
                'vars': {
                    'replicaset_alias': 'replicaset-2',
                    'roles': ['role-2'],
                    'failover_priority': ['r2-leader'],
                    'all_rw': False,
                    'weight': 2,
                    'vshard_group': 'group-2'
                },
                'instances': ['r2-leader', 'r2-replica'],
            },
        ]

        hostvars = {}
        for config in replicasets:
            for i in config['instances']:
                hostvars.update({i: config['vars']})

        res = call_get_replicasets(hostvars)
        self.assertTrue(res.success, msg=res.msg)

        self.assertIn('replicasets', res.meta)
        self.assertIn('join_host', res.meta)

        for config in replicasets:
            alias = config['vars']['replicaset_alias']
            replicaset = None

            for r in res.meta['replicasets']:
                if r['alias'] == alias:
                    replicaset = r
                    break

            self.assertTrue(replicaset is not None)

            config_vars = config['vars']
            self.assertEqual(config_vars['roles'], replicaset.get('roles'))
            self.assertEqual(config_vars['failover_priority'], replicaset.get('failover_priority'))
            self.assertEqual(config_vars['all_rw'], replicaset.get('all_rw'))
            self.assertEqual(config_vars['weight'], replicaset.get('weight'))
            self.assertEqual(config_vars['vshard_group'], replicaset.get('vshard_group'))
