# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest
from instance import Instance
from helpers import add_replicaset

from library.cartridge_edit_topology import edit_topology


def call_edit_topology(console_sock, hostvars, play_hosts=None):
    if play_hosts is None:
        play_hosts = hostvars.keys()

    return edit_topology({
        'console_sock': console_sock,
        'hostvars': hostvars,
        'play_hosts': play_hosts,
    })


class TestEditTopology(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_edit_topology_fails(self):
        add_replicaset(self.instance, 'r1', ['role-1'], ['r1-leader', 'r1-replica'])

        # first call fails
        # change roles
        rpl_vars = {
            'replicaset_alias': 'r1',
            'roles': ['role-1', 'role-2'],  # add one more role
        }

        hostvars = {
            'r1-leader': rpl_vars,
            'r1-replica': rpl_vars,
        }

        self.instance.set_fail_on('edit_topology')
        self.instance.clear_calls('edit_topology')

        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertFalse(res.success, msg=res.msg)
        self.assertEqual(res.msg, "Failed to edit topology: cartridge err")

        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            'replicasets': [{'uuid': 'r1-uuid', 'roles': ['role-1', 'role-2']}]
        })

        # second call fails
        # change only failover priority
        rpl_vars = {
            'replicaset_alias': 'r1',
            'roles': ['role-1'],
            'failover_priority': ['r1-replica', 'r1-leader'],
        }

        hostvars = {
            'r1-leader': rpl_vars,
            'r1-replica': rpl_vars,
        }

        self.instance.set_fail_on('edit_topology')
        self.instance.clear_calls('edit_topology')

        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertFalse(res.success, msg=res.msg)
        self.assertEqual(res.msg, "Failed to edit failover priority: cartridge err")

        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            'replicasets': [{
                'uuid': 'r1-uuid',
                'failover_priority': ['r1-replica-uuid', 'r1-leader-uuid'],
            }],
        })

    def test_create_replicasets(self):
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
        }

        hostvars = {
            'r1-leader': rpl1_vars,
            'r1-replica': rpl1_vars,
            'r1-replica-2': rpl1_vars,
            'r2-leader': rpl2_vars,
            'r2-replica': rpl2_vars,
        }

        # add unjoined instances
        self.instance.add_unjoined_server(alias='r1-leader', uri='r1-leader-uri')
        self.instance.add_unjoined_server(alias='r1-replica', uri='r1-replica-uri')
        self.instance.add_unjoined_server(alias='r1-replica-2', uri='r1-replica-2-uri')
        self.instance.add_unjoined_server(alias='r2-leader', uri='r2-leader-uri')
        # now we don't don't add r2-replica

        # create replicasets with instances not known by cluster (r2-replica)
        self.instance.clear_calls('edit_topology')
        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertFalse(res.success, msg=res.msg)
        self.assertIn("Some of replicaset instances aren't found in cluster: r2-replica", res.msg)
        self.assertEqual(len(self.instance.get_calls('edit_topology')), 0)

        # add r2-replica
        self.instance.add_unjoined_server(alias='r2-replica', uri='r2-replica-uri')

        # create replicasets
        self.instance.clear_calls('edit_topology')
        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 1)

        call = calls[0]
        self.assertNotIn('servers', call)
        self.assertIn('replicasets', call)

        replicasets_opts = call['replicasets']
        self.assertEqual(len(replicasets_opts), 2)

        exp_replicasets_opts = [
            {
                'alias': 'r1',
                'roles': ['role-1', 'role-2'],
                'all_rw': True,
                'weight': 1,
                'vshard_group': 'group-1',
                # no failover priority opt, just join_servers in right order
                'join_servers': [
                    {'uri': uri}
                    for uri in ['r1-leader-uri', 'r1-replica-uri', 'r1-replica-2-uri']
                ]
            },
            {
                'alias': 'r2',
                'roles': ['role-2'],
                # no failover priority opt, just join_servers in right order
                'join_servers': [
                    {'uri': uri}
                    for uri in ['r2-leader-uri', 'r2-replica-uri']
                ]
            }
        ]

        self.assertEqual(replicasets_opts, exp_replicasets_opts)

    def test_change_replicasets(self):
        rpl1_vars = {
            'replicaset_alias': 'r1',
            'roles': ['role-1', 'role-2'],
            'failover_priority': ['r1-leader', 'r1-replica'],
            'all_rw': True,
            'weight': 1,
            'vshard_group': 'group-1'
        }

        add_replicaset(
            instance=self.instance,
            alias=rpl1_vars['replicaset_alias'],
            roles=rpl1_vars['roles'],
            servers=['r1-leader', 'r1-replica', 'r1-replica-2'],
            all_rw=rpl1_vars['all_rw'],
            weight=rpl1_vars['weight'],
            vshard_group=rpl1_vars['vshard_group']
        )

        rpl2_vars = {
            'replicaset_alias': 'r2',
            'roles': ['role-2'],
        }

        add_replicaset(
            self.instance, rpl2_vars['replicaset_alias'], rpl2_vars['roles'],
            ['r2-leader'],
        )

        hostvars = {
            'r1-leader': rpl1_vars,
            'r1-replica': rpl1_vars,
            'r1-replica-2': rpl1_vars,
            'r2-leader': rpl2_vars,
            # don't add r2-replica
        }

        # add unjoined r2-replica
        self.instance.add_unjoined_server(alias='r2-replica', uri='r2-replica-uri')

        # call with the same configuration
        self.instance.clear_calls('edit_topology')
        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)
        calls = self.instance.get_calls('edit_topology')

        self.assertEqual(len(calls), 0)

        # add r2-replica
        hostvars = {
            'r1-leader': rpl1_vars,
            'r1-replica': rpl1_vars,
            'r1-replica-2': rpl1_vars,
            'r2-leader': rpl2_vars,
            'r2-replica': rpl2_vars,
        }

        # call again
        self.instance.clear_calls('edit_topology')
        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)
        calls = self.instance.get_calls('edit_topology')

        self.assertEqual(len(calls), 1)

        call = calls[0]
        self.assertNotIn('servers', call)
        self.assertIn('replicasets', call)

        replicasets_opts = call['replicasets']
        self.assertEqual(len(replicasets_opts), 1)

        exp_replicasets_opts = [
            {
                'uuid': 'r2-uuid',
                # no failover priority opt, just join_servers in right order
                'join_servers': [
                    {'uri': uri}
                    for uri in ['r2-replica-uri']
                ]
            }
        ]

        self.assertEqual(replicasets_opts, exp_replicasets_opts)

        # change both replicasets params
        rpl1_vars = {
            'replicaset_alias': 'r1',
            'roles': ['role-1', 'role-2', 'new-role'],
            'failover_priority': ['r1-leader', 'r1-replica'],
            'all_rw': False,
            'weight': 2,
            'vshard_group': 'group-2'
        }

        rpl2_vars = {
            'replicaset_alias': 'r2',
            'roles': ['new-role'],
            'all_rw': True,
            'weight': 3,
            'vshard_group': 'group-3'
        }

        hostvars = {
            'r1-leader': rpl1_vars,
            'r1-replica': rpl1_vars,
            'r1-replica-2': rpl1_vars,
            'r2-leader': rpl2_vars,
            'r2-replica': rpl2_vars,
        }

        # call with new params
        self.instance.clear_calls('edit_topology')
        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)
        calls = self.instance.get_calls('edit_topology')

        self.assertEqual(len(calls), 1)

        call = calls[0]
        self.assertNotIn('servers', call)
        self.assertIn('replicasets', call)

        replicasets_opts = call['replicasets']
        self.assertEqual(len(replicasets_opts), 2)

        exp_replicasets_opts = [
            {
                'uuid': 'r1-uuid',
                'roles': ['role-1', 'role-2', 'new-role'],
                'all_rw': False,
                'weight': 2,
                'vshard_group': 'group-2',
            },
            {
                'uuid': 'r2-uuid',
                'roles': ['new-role'],
                'all_rw': True,
                'weight': 3,
                'vshard_group': 'group-3'
            }
        ]

        self.assertEqual(replicasets_opts, exp_replicasets_opts)

    def test_change_failover_priority(self):
        add_replicaset(
            self.instance, 'r1', ['role-1', 'role-2'],
            ['r1-leader', 'r1-replica'],
        )

        # add unjoined replicas
        self.instance.add_unjoined_server(alias='r1-replica-2', uri='r1-replica-2-uri')
        self.instance.add_unjoined_server(alias='r1-replica-3', uri='r1-replica-3-uri')

        # change failover priority, don't join any instances
        rpl1_vars = {
            'replicaset_alias': 'r1',
            'roles': ['role-1', 'role-2'],
            'failover_priority': ['r1-replica', 'r1-leader'],
        }

        hostvars = {
            'r1-leader': rpl1_vars,
            'r1-replica': rpl1_vars,
        }

        # call
        self.instance.clear_calls('edit_topology')
        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)
        calls = self.instance.get_calls('edit_topology')

        self.assertEqual(len(calls), 1)

        call = calls[0]
        self.assertNotIn('servers', call)
        self.assertIn('replicasets', call)

        replicasets_opts = call['replicasets']
        self.assertEqual(len(replicasets_opts), 1)

        exp_replicasets_opts = [
            {
                'uuid': 'r1-uuid',
                'failover_priority': ['r1-replica-uuid', 'r1-leader-uuid'],
            },
        ]

        self.assertEqual(replicasets_opts, exp_replicasets_opts)

        # join new instance and add it to the end of failover priority
        # expected one call with join_servers
        rpl1_vars = {
            'replicaset_alias': 'r1',
            'roles': ['role-1', 'role-2'],
            'failover_priority': ['r1-replica', 'r1-leader', 'r1-replica-2'],
        }

        hostvars = {
            'r1-leader': rpl1_vars,
            'r1-replica': rpl1_vars,
            'r1-replica-2': rpl1_vars,
        }

        # call
        self.instance.clear_calls('edit_topology')
        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)
        calls = self.instance.get_calls('edit_topology')

        self.assertEqual(len(calls), 1)

        call = calls[0]
        self.assertNotIn('servers', call)
        self.assertIn('replicasets', call)

        replicasets_opts = call['replicasets']
        self.assertEqual(len(replicasets_opts), 1)

        exp_replicasets_opts = [
            {
                'uuid': 'r1-uuid',
                'join_servers': [
                    {'uri': uri}
                    for uri in ['r1-replica-2-uri']
                ]
            },
        ]

        self.assertEqual(replicasets_opts, exp_replicasets_opts)

        # join new instance and add it to the top of failover priority
        # expected two calls: join_servers and failover_priority
        rpl1_vars = {
            'replicaset_alias': 'r1',
            'roles': ['role-1', 'role-2'],
            'failover_priority': ['r1-replica', 'r1-replica-3', 'r1-replica-2', 'r1-leader'],
        }

        hostvars = {
            'r1-leader': rpl1_vars,
            'r1-replica': rpl1_vars,
            'r1-replica-2': rpl1_vars,
            'r1-replica-3': rpl1_vars,
        }

        # call
        self.instance.clear_calls('edit_topology')
        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)
        calls = self.instance.get_calls('edit_topology')

        self.assertEqual(len(calls), 2, msg=calls)

        join_call = calls[0]
        self.assertNotIn('servers', call)
        self.assertIn('replicasets', call)

        replicasets_opts = join_call['replicasets']
        self.assertEqual(len(replicasets_opts), 1)

        exp_replicasets_opts = [
            {
                'uuid': 'r1-uuid',
                'join_servers': [
                    {'uri': uri}
                    for uri in ['r1-replica-3-uri']
                ]
            },
        ]

        self.assertEqual(replicasets_opts, exp_replicasets_opts)

        filover_priority_call = calls[1]
        self.assertNotIn('servers', call)
        self.assertIn('replicasets', call)

        replicasets_opts = filover_priority_call['replicasets']
        self.assertEqual(len(replicasets_opts), 1)

        exp_replicasets_opts = [
            {
                'uuid': 'r1-uuid',
                'failover_priority': [
                    'r1-replica-uuid', 'r1-replica-3-uuid', 'r1-replica-2-uuid', 'r1-leader-uuid'
                ]
            },
        ]

        self.assertEqual(replicasets_opts, exp_replicasets_opts)

    def test_expel_non_joined_instances(self):
        rpl1_vars = {
            'replicaset_alias': 'r1',
            'roles': ['role-1', 'role-2'],
            'failover_priority': ['r1-leader', 'r1-replica-2']
        }

        rpl2_vars = {
            'replicaset_alias': 'r2',
            'roles': ['role-2'],
        }

        hostvars = {
            'r1-leader': rpl1_vars.copy(),
            'r1-replica': rpl1_vars.copy(),
            'r1-replica-2': rpl1_vars.copy(),
            'r2-leader': rpl2_vars.copy(),
            'r2-replica': rpl2_vars.copy(),
        }

        # mark r1-replica and r2-replica as expelled
        hostvars['r1-replica']['expelled'] = True
        hostvars['r2-replica']['expelled'] = True

        # add unjoined instances
        self.instance.add_unjoined_server(alias='r1-leader', uri='r1-leader-uri')
        self.instance.add_unjoined_server(alias='r1-replica', uri='r1-replica-uri')
        self.instance.add_unjoined_server(alias='r1-replica-2', uri='r1-replica-2-uri')
        self.instance.add_unjoined_server(alias='r2-leader', uri='r2-leader-uri')
        self.instance.add_unjoined_server(alias='r2-replica', uri='r2-replica-uri')

        # edit topology
        self.instance.clear_calls('edit_topology')
        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 1)

        call = calls[0]
        self.assertNotIn('servers', call)  # expelled instances aren't in cluster yet
        self.assertIn('replicasets', call)

        replicasets_opts = call['replicasets']
        self.assertEqual(len(replicasets_opts), 2)

        exp_replicasets_opts = [
            {
                'alias': 'r1',
                'roles': ['role-1', 'role-2'],
                # no failover priority opt, just join_servers in right order
                'join_servers': [
                    {'uri': uri}
                    for uri in ['r1-leader-uri', 'r1-replica-2-uri']  # 'r1-replica-uri' is expelled
                ]
            },
            {
                'alias': 'r2',
                'roles': ['role-2'],
                # no failover priority opt, just join_servers in right order
                'join_servers': [
                    {'uri': uri}
                    for uri in ['r2-leader-uri']  # 'r2-replica-uri' is expelled
                ]
            }
        ]

        self.assertEqual(replicasets_opts, exp_replicasets_opts)

    def test_expel_joined_instances(self):
        add_replicaset(
            self.instance, 'r1', ['role-1', 'role-2'],
            ['r1-leader', 'r1-replica', 'r1-replica-2'],
        )

        add_replicaset(
            self.instance, 'r2', ['role-2'],
            ['r2-leader', 'r2-replica'],
        )

        rpl1_vars = {
            'replicaset_alias': 'r1',
            'roles': ['role-1', 'role-2', 'role-3'],  # add one more role
        }

        rpl2_vars = {
            'replicaset_alias': 'r2',
            'roles': ['role-2'],
        }

        hostvars = {
            'r1-leader': rpl1_vars.copy(),
            'r1-replica': rpl1_vars.copy(),
            'r1-replica-2': rpl1_vars.copy(),
            'r2-leader': rpl2_vars.copy(),
            'r2-replica': rpl2_vars.copy(),
        }

        # mark r1-replica and r2-replica as expelled
        hostvars['r1-replica']['expelled'] = True
        hostvars['r2-replica']['expelled'] = True

        # edit topology
        self.instance.clear_calls('edit_topology')
        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 1)

        call = calls[0]
        self.assertIn('servers', call)
        self.assertIn('replicasets', call)

        replicasets_opts = call['replicasets']

        exp_replicasets_opts = [
            {
                'uuid': 'r1-uuid',
                'roles': ['role-1', 'role-2', 'role-3'],
            },
        ]

        self.assertEqual(replicasets_opts, exp_replicasets_opts)

        servers_opts = call['servers']

        exp_servers_opts = [
            {
                'uuid': 'r1-replica-uuid',
                'expelled': True
            },
            {
                'uuid': 'r2-replica-uuid',
                'expelled': True
            }
        ]

        self.assertEqual(servers_opts, exp_servers_opts)

    def tearDown(self):
        self.instance.stop()
