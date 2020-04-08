# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest
from instance import Instance
from helpers import add_replicaset

from library.cartridge_manage_replicaset import manage_replicaset

HEALTHY_TIMEOUT = 0.1


def call_manage_replicaset(control_sock,
                           alias,
                           failover_priority,
                           instances,
                           roles=None,
                           all_rw=None,
                           weight=None,
                           vshard_group=None):
    return manage_replicaset({
        'control_sock': control_sock,
        'replicaset': {
            'alias': alias,
            'failover_priority': failover_priority,
            'roles': roles,
            'instances': instances,
            'all_rw': all_rw,
            'weight': weight,
            'vshard_group': vshard_group,
        },
        'healthy_timeout': HEALTHY_TIMEOUT,
    })


class TestManageInstance(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_create_replicaset(self):
        # create replicaset with instances not known by cluster
        self.instance.clear_calls('edit_topology')
        res = call_manage_replicaset(
            self.console_sock,
            alias='r1',
            failover_priority=['r1-master'],
            instances=['r1-master', 'r1-replica'],
            roles=['role-1']
        )
        self.assertFalse(res.success, msg=res.msg)
        self.assertIn('Leader "r1-master" (replicaset "r1") not found is cluster', res.msg)
        self.assertEqual(len(self.instance.get_calls('edit_topology')), 0)

        # add unjoined
        self.instance.add_unjoined_server(alias='r1-master', uri='r1-master-uri')
        self.instance.add_unjoined_server(alias='r1-replica', uri='r1-replica-uri')

        # create replicaset with instances known by cluster
        self.instance.clear_calls('edit_topology')
        res = call_manage_replicaset(
            self.console_sock,
            alias='r1',
            failover_priority=['r1-master'],
            instances=['r1-master', 'r1-replica'],
            roles=['role-1']
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        # check performed `edit_topology` calls
        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 2)
        join_leader_call = calls[0]
        join_replica_call = calls[1]

        # check join leader call
        self.assertIn('replicasets', join_leader_call)
        self.assertEqual(len(join_leader_call['replicasets']), 1)
        r_params = join_leader_call['replicasets'][0]
        self.assertEqual(r_params, {
            'alias': 'r1',
            'roles': ['role-1'],
            'join_servers': [{'uri': 'r1-master-uri'}],
        })

        # check join replica call
        self.assertIn('replicasets', join_replica_call)
        self.assertEqual(len(join_replica_call['replicasets']), 1)
        r_params = join_replica_call['replicasets'][0]
        self.assertEqual(r_params, {
            'uuid': 'r1-uuid',
            'join_servers': [{'uri': 'r1-replica-uri'}],
        })

        # repeat the call (res.changed should be false)
        self.instance.clear_calls('edit_topology')
        res = call_manage_replicaset(
            self.console_sock,
            alias='r1',
            failover_priority=['r1-master'],
            instances=['r1-master', 'r1-replica'],
            roles=['role-1']
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        # check performed `edit_topology` calls
        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 1)
        self.assertIn('replicasets', calls[0])
        r_params = calls[0]['replicasets'][0]
        self.assertEqual(r_params, {
            'uuid': 'r1-uuid',
            'roles': ['role-1'],
            'failover_priority': ['r1-master-uuid'],
        })

    def test_edit_replicaset_parameters(self):
        add_replicaset(
            self.instance,
            alias='r1',
            roles=['role-1'],
            servers=['r1-master'],
        )

        params = {
            'all_rw': True,
            'weight': 1,
            'vshard_group': 'hot',
            'roles': ['role-2'],
        }

        for param, value in params.items():
            self.instance.clear_calls('edit_topology')

            res = call_manage_replicaset(
                self.console_sock,
                alias='r1',
                failover_priority=['r1-master'],
                instances=['r1-master'],
                **{param: value},
            )
            self.assertTrue(res.success, msg=res.msg)
            self.assertTrue(res.changed)

            # check performed `edit_topology` calls
            calls = self.instance.get_calls('edit_topology')
            self.assertEqual(len(calls), 1)
            self.assertIn('replicasets', calls[0])
            r_params = calls[0]['replicasets'][0]
            self.assertEqual(r_params, {
                'uuid': 'r1-uuid',
                'failover_priority': ['r1-master-uuid'],
                **{param: value},
            })

            # set the same parameter again (res.changed should be false)
            self.instance.clear_calls('edit_topology')
            res = call_manage_replicaset(
                self.console_sock,
                alias='r1',
                failover_priority=['r1-master'],
                instances=['r1-master'],
                **{param: value},
            )
            self.assertTrue(res.success, msg=res.msg)
            self.assertFalse(res.changed)

            # check performed `edit_topology` calls
            calls = self.instance.get_calls('edit_topology')
            self.assertEqual(len(calls), 1)
            self.assertIn('replicasets', calls[0])
            r_params = calls[0]['replicasets'][0]
            self.assertEqual(r_params, {
                'uuid': 'r1-uuid',
                'failover_priority': ['r1-master-uuid'],
                **{param: value},
            })

    def test_joining_new_servers(self):
        add_replicaset(
            self.instance,
            alias='r1',
            roles=['role-1'],
            servers=['r1-master', 'r1-replica'],
        )

        # add unjoined
        self.instance.add_unjoined_server(
            alias='r1-new-master',
            uri='r1-new-master-uri'
        )

        # join new server and set it to be a new master
        self.instance.clear_calls('edit_topology')
        res = call_manage_replicaset(
            self.console_sock,
            alias='r1',
            failover_priority=['r1-new-master', 'r1-master'],
            instances=['r1-master', 'r1-replica', 'r1-new-master'],
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        # check performed `edit_topology` calls
        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 2)
        join_call = calls[0]
        edit_priority_call = calls[1]

        self.assertIn('replicasets', join_call)
        r_params = join_call['replicasets'][0]
        self.assertEqual(r_params, {
            'uuid': 'r1-uuid',
            'join_servers': [{'uri': 'r1-new-master-uri'}],
        })

        self.assertIn('replicasets', edit_priority_call)
        r_params = edit_priority_call['replicasets'][0]
        self.assertEqual(r_params, {
            'uuid': 'r1-uuid',
            'failover_priority': ['r1-new-master-uuid', 'r1-master-uuid'],
        })

        # call again (res.changed should be false)
        res = call_manage_replicaset(
            self.console_sock,
            alias='r1',
            failover_priority=['r1-new-master', 'r1-master'],
            instances=['r1-master', 'r1-replica', 'r1-new-master'],
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

    def test_fail_on_edit_topology(self):
        # fail on create
        self.instance.add_unjoined_server(alias='r1-master', uri='r1-master-uri')
        self.instance.clear_calls('edit_topology')
        self.instance.set_fail_on('edit_topology')

        # create replicaset with instances known by cluster
        self.instance.clear_calls('edit_topology')
        res = call_manage_replicaset(
            self.console_sock,
            alias='r1',
            failover_priority=['r1-master'],
            instances=['r1-master'],
            roles=['role-1']
        )
        self.assertFalse(res.success)
        self.assertIn('Failed to create', res.msg)
        self.assertIn('cartridge err', res.msg)

        # fail on edit
        add_replicaset(
            self.instance,
            alias='r1',
            roles=['role-1'],
            servers=['r1-master', 'r1-replica'],
        )

        self.instance.clear_calls('edit_topology')
        self.instance.set_fail_on('edit_topology')

        res = call_manage_replicaset(
            self.console_sock,
            alias='r1',
            failover_priority=['r1-master'],
            instances=['r1-master'],
            roles=['role-1', 'role-2'],
        )
        self.assertFalse(res.success)
        self.assertIn('Failed to edit replicaset', res.msg)
        self.assertIn('cartridge err', res.msg)

        self.instance.set_fail_on('edit_topology', False)

    def test_replicaset_in_unhealthy(self):
        # try to edit unhealthy replicaset
        add_replicaset(
            self.instance,
            alias='r1',
            roles=['role-1'],
            servers=['r1-master'],
            status='unhealthy',
        )

        res = call_manage_replicaset(
            self.console_sock,
            alias='r1',
            roles=['role-2'],
            failover_priority=['r1-master'],
            instances=['r1-master'],
        )

        self.assertFalse(res.success)
        self.assertIn('Replicaset "r1" is not healthy', res.msg)

        # replicaset becomes unhealthy after creation
        self.instance.set_variable('become_unhealthy_after_edit', True)

        self.instance.add_unjoined_server(alias='r2-master', uri='r2-master-uri')

        res = call_manage_replicaset(
            self.console_sock,
            alias='r2',
            roles=['role-2'],
            failover_priority=['r2-master'],
            instances=['r2-master'],
        )
        self.assertFalse(res.success)
        self.assertIn('Replicaset "r2" is not healthy', res.msg)

        # replicaset becomes unhealthy after edit
        self.instance.set_variable('become_unhealthy_after_edit', True)

        add_replicaset(
            self.instance,
            alias='r3',
            roles=['role-1'],
            servers=['r3-master'],
            status='unhealthy',
        )

        res = call_manage_replicaset(
            self.console_sock,
            alias='r3',
            roles=['role-2'],
            failover_priority=['r3-master'],
            instances=['r3-master'],
        )
        self.assertFalse(res.success)
        self.assertIn('Replicaset "r3" is not healthy', res.msg)

    def tearDown(self):
        self.instance.stop()
