# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest

from library.cartridge_edit_topology import get_configured_replicasets
from library.cartridge_edit_topology import get_instances_to_expel
from library.cartridge_edit_topology import get_edit_replicaset_params


def call_get_configured_replicasets(hostvars, play_hosts=None):
    if play_hosts is None:
        play_hosts = hostvars.keys()

    return get_configured_replicasets(hostvars, play_hosts)


class TestGetConfiguredReplicasets(unittest.TestCase):
    def test_empty_replicasets(self):
        replicasets = call_get_configured_replicasets({
            'instance-1': {
                'config': {
                    'advertise_uri': 'localhost:3301',
                }
            }
        })
        self.assertEqual(len(replicasets), 0)

    def test_instances_skipped(self):
        hostvars = {
            'instance-expelled': {  # expelled
                'replicaset_alias': 'replicaset-1',
                'expelled': True,
            },
            'instance-2': {
                'replicaset_alias': 'replicaset-1',
            },
            'not-play-host': {  # not in play hosts
                'replicaset_alias': 'replicaset-1',
            },
            'instance-4': {
                'replicaset_alias': 'replicaset-1',
            },
            'instance-stateboard': {  # stateboard
                'replicaset_alias': 'replicaset-1',
                'stateboard': True,
            },
        }
        play_hosts = ['instance-expelled', 'instance-2', 'instance-4', 'instance-stateboard']

        replicasets = call_get_configured_replicasets(hostvars, play_hosts)
        self.assertEqual(len(replicasets), 1)
        replicaset = replicasets['replicaset-1']

        self.assertEqual(len(replicaset), 7)

        self.assertEqual(replicaset['alias'], 'replicaset-1')
        self.assertEqual(set(replicaset['instances']), set(['instance-2', 'instance-4']))

        self.assertEqual(replicaset['roles'], None)
        self.assertEqual(replicaset['failover_priority'], None)
        self.assertEqual(replicaset['all_rw'], None)
        self.assertEqual(replicaset['weight'], None)
        self.assertEqual(replicaset['vshard_group'], None)

    def test_two_replicasets(self):
        rpl1_vars = {
            'replicaset_alias': 'r1',
            'roles': ['role-1', 'role-2'],
            'failover_priority': ['r1-leader', 'r1-replica'],
            'all_rw': True,
            'weight': 1,
            'vshard_group': 'group-1'
        }

        rpl2_vars = {
            'replicaset_alias': 'r2',
            'roles': ['role-2'],
            'failover_priority': ['r2-leader'],
            'all_rw': False,
            'weight': 2,
            'vshard_group': 'group-2'
        }

        hostvars = {
            'r1-leader': rpl1_vars,
            'r1-replica': rpl1_vars,
            'r2-leader': rpl2_vars,
            'r2-replica': rpl2_vars,
        }

        replicasets = call_get_configured_replicasets(hostvars)
        self.assertEqual(len(replicasets), 2)

        for alias, replicaset in replicasets.items():
            self.assertIn(alias, ['r1', 'r2'])

            if alias == 'r1':
                rpl_conf = rpl1_vars
            elif alias == 'r2':
                rpl_conf = rpl2_vars

            self.assertEqual(replicaset['roles'], rpl_conf.get('roles'))
            self.assertEqual(replicaset['failover_priority'], rpl_conf.get('failover_priority'))
            self.assertEqual(replicaset['all_rw'], rpl_conf.get('all_rw'))
            self.assertEqual(replicaset['weight'], rpl_conf.get('weight'))
            self.assertEqual(replicaset['vshard_group'], rpl_conf.get('vshard_group'))


class TestGetInstancesToExpel(unittest.TestCase):
    def test_get_instances_to_expel(self):
        hostvars = {
            'instance-expelled-1': {  # expelled
                'replicaset_alias': 'replicaset-1',
                'expelled': True,
            },
            'instance-expelled-2': {  # expelled
                'replicaset_alias': 'replicaset-1',
                'expelled': True,
            },
            'instance-2': {
                'replicaset_alias': 'replicaset-1',
            },
            'not-play-host': {  # not in play hosts
                'expelled': True
            },
            'instance-4': {
                'replicaset_alias': 'replicaset-1',
            },
            'instance-stateboard': {  # stateboard
                'expelled': True,
                'stateboard': True,
            },
        }

        # found expelled instances
        play_hosts = [
            'instance-expelled-1', 'instance-2', 'instance-4', 'instance-stateboard', 'instance-expelled-2',
        ]

        instances_to_expel = get_instances_to_expel(hostvars, play_hosts)
        self.assertEqual(set(instances_to_expel), {
            'instance-expelled-1', 'instance-expelled-2'
        })

        # not found expelled instances
        play_hosts = [
            'instance-2', 'instance-4', 'instance-stateboard'
        ]

        instances_to_expel = get_instances_to_expel(hostvars, play_hosts)
        self.assertEqual(len(instances_to_expel), 0)


class TestGetEditReplicasetParams(unittest.TestCase):
    def test_create_replicaset(self):
        cluster_instances = {
            alias: {'uri': '%s-uri' % alias, 'alias': alias}
            for alias in ['i1', 'i2', 'i3', 'i4']
        }

        cluster_replicaset = None

        # no additional params
        replicaset = {
            'alias': 'r1',
            'instances': ['i3', 'i2', 'i4', 'i1'],
            'failover_priority': ['i1', 'i2', 'i3'],
        }

        params, err = get_edit_replicaset_params(replicaset, cluster_replicaset, cluster_instances)
        self.assertIsNone(err)
        self.assertEqual(params, {
            'alias': 'r1',
            'join_servers': [
                {'uri': uri}
                for uri in ['i1-uri', 'i2-uri', 'i3-uri', 'i4-uri']
            ]
        })

        # with additional params
        additional_params = {
            'roles': ['role-1', 'role-2'],
            'all_rw': True,
            'weight': 123,
            'vshard_group': 'hot',
        }

        for param_name, param_value in additional_params.items():
            replicaset = {
                'alias': 'r1',
                'instances': ['i3', 'i2', 'i4', 'i1'],
                'failover_priority': ['i1', 'i2', 'i3'],
                param_name: param_value,
            }

            params, err = get_edit_replicaset_params(replicaset, cluster_replicaset, cluster_instances)
            self.assertIsNone(err)
            self.assertEqual(params, {
                'alias': 'r1',
                param_name: param_value,
                'join_servers': [
                    {'uri': uri}
                    for uri in ['i1-uri', 'i2-uri', 'i3-uri', 'i4-uri']
                ]
            })

        # instances that not found in cluster
        replicaset = {
            'alias': 'r1',
            'instances': ['i3', 'unknown-1', 'i2', 'i4', 'i1', 'unknown-2'],
            'failover_priority': ['i1', 'i2', 'i3'],
        }

        params, err = get_edit_replicaset_params(replicaset, cluster_replicaset, cluster_instances)
        self.assertIsNone(params)
        self.assertIn("Some of replicaset instances aren't found in cluster: ", err)
        self.assertTrue(
            "in cluster: unknown-2, unknown-1" in err or "in cluster: unknown-1, unknown-2" in err
        )

        # failover_priority contains instances that not found in cluster
        replicaset = {
            'alias': 'r1',
            'instances': ['i3', 'i2', 'i4', 'i1'],
            'failover_priority': ['i1', 'unknown-2', 'i2', 'i3', 'unknown-1'],
        }

        params, err = get_edit_replicaset_params(replicaset, cluster_replicaset, cluster_instances)
        self.assertIsNone(params)
        self.assertIn("Some of instances specified in failover_priority aren't found in cluster: ", err)
        self.assertTrue(
            "in cluster: unknown-2, unknown-1" in err or "in cluster: unknown-1, unknown-2" in err
        )

    def test_change_replicaset_params(self):
        cluster_instances = {
            alias: {'uri': '%s-uri' % alias, 'alias': alias}
            for alias in ['i1', 'i2', 'i3', 'i4']
        }

        # replicaset wasn't changed
        cluster_replicaset = {
            'uuid': 'r1-uuid',
            'alias': 'r1',
            'instances': ['i1', 'i2', 'i3', 'i4'],
            'roles': ['role-1', 'role-3', 'role-2'],
            'all_rw': False,
            'weight': 321,
            'vshard_group': 'cold',
        }

        replicaset = {
            'alias': 'r1',
            'instances': ['i3', 'i2', 'i4', 'i1'],
            'failover_priority': ['i1', 'i2', 'i3'],
            'roles': ['role-1', 'role-3', 'role-2'],
            'all_rw': False,
            'weight': 321,
            'vshard_group': 'cold',
        }

        params, err = get_edit_replicaset_params(replicaset, cluster_replicaset, cluster_instances)
        self.assertIsNone(err)
        self.assertIsNone(params)

        # additional params changed
        additional_params = {
            'roles': ['role-1', 'role-2'],
            'all_rw': True,
            'weight': 123,
            'vshard_group': 'hot',
        }

        new_additional_params = {
            'roles': ['role-1', 'role-3', 'role-2'],
            'all_rw': False,
            'weight': 321,
            'vshard_group': 'cold',
        }

        for param_name, param_value in additional_params.items():
            new_param_value = new_additional_params[param_name]

            # value changed
            cluster_replicaset = {
                'uuid': 'r1-uuid',
                'alias': 'r1',
                'instances': ['i1', 'i2', 'i3', 'i4'],
                param_name: param_value,
            }

            replicaset = {
                'alias': 'r1',
                'instances': ['i3', 'i2', 'i4', 'i1'],
                'failover_priority': ['i1', 'i2', 'i3'],
                param_name: new_param_value,
            }

            params, err = get_edit_replicaset_params(replicaset, cluster_replicaset, cluster_instances)
            self.assertIsNone(err)
            self.assertEqual(params, {
                'uuid': 'r1-uuid',
                param_name: new_param_value,
            })

            # value was empty, but now is added
            cluster_replicaset = {
                'uuid': 'r1-uuid',
                'alias': 'r1',
                'instances': ['i1', 'i2', 'i3', 'i4'],
            }

            replicaset = {
                'alias': 'r1',
                'instances': ['i3', 'i2', 'i4', 'i1'],
                'failover_priority': ['i1', 'i2', 'i3'],
                param_name: new_param_value,
            }

            params, err = get_edit_replicaset_params(replicaset, cluster_replicaset, cluster_instances)
            self.assertIsNone(err)
            self.assertEqual(params, {
                'uuid': 'r1-uuid',
                param_name: new_param_value,
            })

            # value was set, but now is empty
            cluster_replicaset = {
                'uuid': 'r1-uuid',
                'alias': 'r1',
                'instances': ['i1', 'i2', 'i3', 'i4'],
                param_name: param_value,
            }

            replicaset = {
                'alias': 'r1',
                'instances': ['i3', 'i2', 'i4', 'i1'],
                'failover_priority': ['i1', 'i2', 'i3'],
            }

            params, err = get_edit_replicaset_params(replicaset, cluster_replicaset, cluster_instances)
            self.assertIsNone(err)
            self.assertIsNone(params)

    def test_join_new_instances(self):
        cluster_instances = {
            alias: {'uri': '%s-uri' % alias, 'alias': alias}
            for alias in ['i1', 'i2', 'i3', 'i4']
        }

        # replicaset wasn't changed
        cluster_replicaset = {
            'uuid': 'r1-uuid',
            'alias': 'r1',
            'instances': ['i1', 'i4'],
        }

        replicaset = {
            'alias': 'r1',
            'instances': ['i3', 'i2', 'i4', 'i1'],
            'failover_priority': ['i1', 'i2', 'i3'],
        }

        params, err = get_edit_replicaset_params(replicaset, cluster_replicaset, cluster_instances)
        self.assertIsNone(err)

        self.assertEqual(len(params), 2)
        self.assertEqual(params['uuid'], 'r1-uuid')
        self.assertEqual(len(params['join_servers']), 2)
        self.assertTrue(all([
            {'uri': uri} in params['join_servers'] for uri in ['i2-uri', 'i3-uri']
        ]))

    def test_less_instances_specified(self):
        cluster_instances = {
            alias: {'uri': '%s-uri' % alias, 'alias': alias}
            for alias in ['i1', 'i2', 'i3', 'i4']
        }

        # replicaset wasn't changed
        cluster_replicaset = {
            'uuid': 'r1-uuid',
            'alias': 'r1',
            'instances': ['i1', 'i2', 'i3', 'i4'],
        }

        replicaset = {
            'alias': 'r1',
            'instances': ['i3'],
        }

        params, err = get_edit_replicaset_params(replicaset, cluster_replicaset, cluster_instances)
        self.assertIsNone(err)
        self.assertIsNone(params)
