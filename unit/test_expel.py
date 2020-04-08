# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest
from instance import Instance
from helpers import add_replicaset

from library.cartridge_expel_instance import expel_intstance


def call_expel_intstance(control_sock, alias):
    return expel_intstance({
        'control_sock': control_sock,
        'alias': alias,
    })


class TestExpelInstance(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_non_existent_instance(self):
        self.instance.clear_calls('edit_topology')

        res = call_expel_intstance(self.console_sock, 'non-existent-instance')
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 0)

    def test_unjoined_instance(self):
        ALIAS = 'instance'
        self.instance.add_unjoined_server(alias=ALIAS, uri='{}-uri'.format(ALIAS))

        self.instance.clear_calls('edit_topology')

        res = call_expel_intstance(self.console_sock, ALIAS)
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 0)

    def test_instance_from_replicaset(self):
        add_replicaset(
            self.instance,
            alias='r1',
            roles=['role-1'],
            servers=['r1-master', 'r1-replica'],
        )

        self.instance.clear_calls('edit_topology')
        res = call_expel_intstance(self.console_sock, 'r1-master')
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        # check `edit_topology` call
        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 1)
        self.assertIn('servers', calls[0])
        self.assertEqual(len(calls[0]['servers']), 1)
        s_params = calls[0]['servers'][0]
        self.assertEqual(s_params, {
            'uuid': 'r1-master-uuid',
            'expelled': True,
        })

        # call again (res.changed should be false)
        # in fact, bacause server is expelled from topology
        self.instance.clear_calls('edit_topology')
        res = call_expel_intstance(self.console_sock, 'r1-master')
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('edit_topology')
        self.assertEqual(len(calls), 0)

    def test_fail_on_edit_topology(self):
        add_replicaset(
            self.instance,
            alias='r1',
            roles=['role-1'],
            servers=['r1-master', 'r1-replica'],
        )

        self.instance.clear_calls('edit_topology')
        self.instance.set_fail_on('edit_topology')

        res = call_expel_intstance(self.console_sock, 'r1-master')
        self.assertFalse(res.success)
        self.assertIn('Failed to expel instance', res.msg)

    def tearDown(self):
        self.instance.stop()
