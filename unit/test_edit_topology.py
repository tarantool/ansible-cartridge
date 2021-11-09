import sys
import unittest

from parameterized import parameterized

import module_utils.helpers as helpers
from unit.instance import Instance

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_edit_topology import edit_topology


def call_edit_topology(console_sock, module_hostvars, play_hosts=None, timeout=60, allow_missed_instances=False):
    if play_hosts is None:
        play_hosts = module_hostvars.keys()

    return edit_topology({
        'console_sock': console_sock,
        'module_hostvars': module_hostvars,
        'play_hosts': play_hosts,
        'healthy_timeout': timeout,
        'allow_missed_instances': allow_missed_instances,
    })


def assert_err_soft_mode(t, allow_missed_instances, res, exp_replicasets_opts, expected_err):
    res_json = res.get_exit_json()

    if allow_missed_instances:
        t.assertEqual(res.failed, False)
        t.assertEqual(list(set(res_json['warnings'])), [expected_err])

        calls = t.instance.get_calls('edit_topology')
        call = calls[0]
        t.assertNotIn('servers', call)
        t.assertIn('replicasets', call)

        replicasets_opts = call['replicasets']
        t.assertEqual(replicasets_opts, exp_replicasets_opts)
    else:
        t.assertEqual(res.failed, True)
        t.assertIn(expected_err, res_json['msg'])
        t.assertEqual(len(t.instance.get_calls('edit_topology')), 0)


class TestEditTopology(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

        self.instance = Instance()
        self.console_sock = self.instance.console_sock
        self.cookie = self.instance.cluster_cookie

        self.instance.start()

    @parameterized.expand([
        [True],  # allow_missed_instances
        [False],
    ])
    def test_edit_topology_fails(self, allow_missed_instances):
        self.instance.add_replicaset(
            alias='r1',
            instances=['r1-leader', 'r1-replica'],
            all_rw=False,
        )

        # first call fails
        # set all_rw to true
        rpl_vars = {
            'replicaset_alias': 'r1',
            'all_rw': True
        }

        hostvars = {
            'r1-leader': rpl_vars,
            'r1-replica': rpl_vars,
        }

        self.instance.set_fail_on('edit_topology')
        self.instance.clear_calls('edit_topology')

        res = call_edit_topology(
            self.console_sock,
            hostvars,
            allow_missed_instances=allow_missed_instances,
        )
        self.assertTrue(res.failed, msg=res.msg)
        self.assertEqual(res.msg, "Failed to edit topology: cartridge err")

        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            'replicasets': [{'uuid': 'r1-uuid', 'all_rw': True}]
        })

        # second call fails
        # change only failover priority
        rpl_vars = {
            'replicaset_alias': 'r1',
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
            hostvars,
            allow_missed_instances=allow_missed_instances,
        )
        self.assertTrue(res.failed, msg=res.msg)
        self.assertEqual(res.msg, "Failed to edit topology: cartridge err")

        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            'replicasets': [{
                'uuid': 'r1-uuid',
                'failover_priority': ['r1-replica-uuid', 'r1-leader-uuid'],
            }],
        })

    @parameterized.expand([
        [True],  # allow_missed_instances
        [False],
    ])
    def test_create_replicasets(self, allow_missed_instances):
        self.instance.cfg_roles({'name': 'role-1'}, {'name': 'role-2'})

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

        self.instance.add_membership_members([
            {'alias': 'r1-leader', 'uri': 'r1-leader-uri'},
            {'alias': 'r1-replica', 'uri': 'r1-replica-uri'},
            {'alias': 'r1-replica-2', 'uri': 'r1-replica-2-uri'},
            {'alias': 'r2-leader', 'uri': 'r2-leader-uri'},
        ])

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
                    for uri in ['r2-leader-uri']
                ]
            }
        ]

        # now we don't add r2-replica

        # create replicasets with instances not known by cluster (r2-replica)
        self.instance.clear_calls('edit_topology')
        helpers.WARNINGS = []
        res = call_edit_topology(
            self.console_sock,
            hostvars,
            allow_missed_instances=allow_missed_instances,
        )

        expected_err = "Some of replicaset instances aren't found in cluster: r2-replica"
        assert_err_soft_mode(self, allow_missed_instances, res, exp_replicasets_opts, expected_err)

        if not allow_missed_instances:
            # add r2-replica
            self.instance.add_membership_members([
                {'alias': 'r2-replica', 'uri': 'r2-replica-uri'},
            ])

            exp_replicasets_opts[1]['join_servers'].append({
                'uri': 'r2-replica-uri',
            })

            # create replicasets
            self.instance.clear_calls('edit_topology')
            res = call_edit_topology(
                self.console_sock,
                hostvars
            )
            self.assertFalse(res.failed, msg=res.msg)
            self.assertTrue(res.changed)

            calls = self.instance.get_calls('edit_topology')
            self.assertEqual(len(calls), 1)

            call = calls[0]
            self.assertNotIn('servers', call)
            self.assertIn('replicasets', call)

            replicasets_opts = call['replicasets']
            self.assertEqual(len(replicasets_opts), 2)

            self.assertEqual(replicasets_opts, exp_replicasets_opts)

    @parameterized.expand([
        [True],  # allow_missed_instances
        [False],
    ])
    def test_change_replicasets(self, allow_missed_instances):
        self.instance.cfg_roles(
            {'name': 'role-1', 'dependencies': ['role-1-dep', 'role-1-dep-hidden']},
            {'name': 'role-1-dep'},
            {'name': 'role-1-dep-hidden', 'hidden': True},
            {'name': 'role-2'},
            {'name': 'role-3-permanent', 'permanent': True},
            {'name': 'vshard-storage', 'known': True},
        )

        rpl1_vars = {
            'replicaset_alias': 'r1',
            'roles': ['vshard-storage', 'role-2'],
            'failover_priority': ['r1-leader', 'r1-replica'],
            'all_rw': True,
            'weight': 1,
            'vshard_group': 'group-1'
        }

        self.instance.add_replicaset(
            alias=rpl1_vars['replicaset_alias'],
            instances=['r1-leader', 'r1-replica', 'r1-replica-2'],
            roles=rpl1_vars['roles'],
            all_rw=rpl1_vars['all_rw'],
            weight=rpl1_vars['weight'],
            vshard_group=rpl1_vars['vshard_group']
        )

        rpl2_vars = {
            'replicaset_alias': 'r2',
            'roles': ['vshard-storage'],
        }

        self.instance.add_replicaset(
            alias=rpl2_vars['replicaset_alias'],
            instances=['r2-leader'],
            roles=rpl2_vars['roles'],
        )

        hostvars = {
            'r1-leader': rpl1_vars,
            'r1-replica': rpl1_vars,
            'r1-replica-2': rpl1_vars,
            'r2-leader': rpl2_vars,
            # don't add r2-replica
        }

        # add unjoined r2-replica
        self.instance.add_membership_members([
            {'alias': 'r2-replica', 'uri': 'r2-replica-uri'},
        ])

        # call with the same configuration
        self.instance.clear_calls('edit_topology')
        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertFalse(res.failed, msg=res.msg)
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
        self.assertFalse(res.failed, msg=res.msg)
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
        self.assertFalse(res.failed, msg=res.msg)
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

    @parameterized.expand([
        [True],  # allow_missed_instances
        [False],
    ])
    def test_change_failover_priority(self, allow_missed_instances):
        self.instance.add_replicaset(
            alias='r1',
            instances=['r1-leader', 'r1-replica'],
        )

        # add unjoined replicas
        self.instance.add_membership_members([
            {'alias': 'r1-replica-2', 'uri': 'r1-replica-2-uri'},
            {'alias': 'r1-replica-3', 'uri': 'r1-replica-3-uri'},
        ])

        # change failover priority, don't join any instances
        rpl1_vars = {
            'replicaset_alias': 'r1',
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
        self.assertFalse(res.failed, msg=res.msg)
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
        self.assertFalse(res.failed, msg=res.msg)
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
        self.assertFalse(res.failed, msg=res.msg)
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

        failover_priority_call = calls[1]
        self.assertNotIn('servers', call)
        self.assertIn('replicasets', call)

        replicasets_opts = failover_priority_call['replicasets']
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

    @parameterized.expand([
        [True],  # allow_missed_instances
        [False],
    ])
    def test_expel_non_joined_instances(self, allow_missed_instances):
        rpl1_vars = {
            'replicaset_alias': 'r1',
            'failover_priority': ['r1-leader', 'r1-replica-2'],
            'all_rw': True,
        }

        rpl2_vars = {
            'replicaset_alias': 'r2',
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
        self.instance.add_membership_members([
            {'alias': 'r1-leader', 'uri': 'r1-leader-uri'},
            {'alias': 'r1-replica', 'uri': 'r1-replica-uri'},
            {'alias': 'r1-replica-2', 'uri': 'r1-replica-2-uri'},
            {'alias': 'r2-leader', 'uri': 'r2-leader-uri'},
            {'alias': 'r2-replica', 'uri': 'r2-replica-uri'},
        ])

        # edit topology
        self.instance.clear_calls('edit_topology')
        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertFalse(res.failed, msg=res.msg)
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
                'all_rw': True,
                # no failover priority opt, just join_servers in right order
                'join_servers': [
                    {'uri': uri}
                    for uri in ['r1-leader-uri', 'r1-replica-2-uri']  # 'r1-replica-uri' is expelled
                ]
            },
            {
                'alias': 'r2',
                # no failover priority opt, just join_servers in right order
                'join_servers': [
                    {'uri': uri}
                    for uri in ['r2-leader-uri']  # 'r2-replica-uri' is expelled
                ]
            }
        ]

        self.assertEqual(replicasets_opts, exp_replicasets_opts)

    @parameterized.expand([
        [True],  # allow_missed_instances
        [False],
    ])
    def test_expel_joined_instances(self, allow_missed_instances):
        self.instance.add_replicaset(
            alias='r1',
            instances=['r1-leader', 'r1-replica', 'r1-replica-2'],
            all_rw=False,
        )

        self.instance.add_replicaset(
            alias='r2',
            instances=['r2-leader', 'r2-replica'],
            all_rw=False,
        )

        rpl1_vars = {
            'replicaset_alias': 'r1',
            'all_rw': True
        }

        rpl2_vars = {
            'replicaset_alias': 'r2',
            'all_rw': False,
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
        self.assertFalse(res.failed, msg=res.msg)
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
                'all_rw': True,
            },
        ]

        self.assertEqual(replicasets_opts, exp_replicasets_opts)

        servers_opts = sorted(call['servers'], key=lambda s: s['uuid'])

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

    @parameterized.expand([
        [True],  # allow_missed_instances
        [False],
    ])
    def test_configure_instances(self, allow_missed_instances):
        self.instance.add_replicaset(
            alias='r1',
            instances=['r1-leader', 'r1-replica'],
            all_rw=False,
        )

        self.instance.add_membership_members([
            {'alias': 'r1-replica-2', 'uri': 'r1-replica-2-uri'},
        ])

        # join 'r1-replica-2', set ot to failover_priority top
        # set zones for 'r1-replica' and 'r1-replica-2'
        rpl1_vars = {
            'replicaset_alias': 'r1',
            'all_rw': False,
            'failover_priority': ['r1-replica-2'],
        }

        r1_leader_vars = rpl1_vars.copy()
        r1_replica_vars = {'zone': 'Hogwarts'}
        r1_replica_vars.update(rpl1_vars)
        r1_replica_2_vars = {'zone': 'Mordor'}
        r1_replica_2_vars.update(rpl1_vars)

        hostvars = {
            'r1-leader': r1_leader_vars,
            'r1-replica': r1_replica_vars,
            'r1-replica-2': r1_replica_2_vars,
        }

        # edit topology
        self.instance.clear_calls('edit_topology')
        res = call_edit_topology(
            self.console_sock,
            hostvars
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 2)

        # first call - join new instance and set r1-replica zone
        self.assertEqual(calls[0], {
            'replicasets': [{
                'uuid': 'r1-uuid',
                'join_servers': [{'uri': 'r1-replica-2-uri'}],
            }],
            'servers': [{
                'uuid': 'r1-replica-uuid',
                'zone': 'Hogwarts'
            }]
        })

        # first call - set failover_priority and r1-replica-2 zone
        self.assertEqual(calls[1], {
            'replicasets': [{
                'uuid': 'r1-uuid',
                'failover_priority': ['r1-replica-2-uuid'],
            }],
            'servers': [{
                'uuid': 'r1-replica-2-uuid',
                'zone': 'Mordor'
            }]
        })

    def tearDown(self):
        self.instance.stop()
        del self.instance
