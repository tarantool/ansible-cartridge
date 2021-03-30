import sys
import unittest

import module_utils.helpers as helpers

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_get_single_instances_for_each_machine import get_one_not_expelled_instance_for_machine


def call_get_one_not_expelled_instance_for_machine(hostvars, play_hosts=None):
    if play_hosts is None:
        play_hosts = hostvars.keys()

    return get_one_not_expelled_instance_for_machine({
        'hostvars': hostvars,
        'play_hosts': play_hosts,
    })


class TestGetOneInstanceForMachine(unittest.TestCase):
    def setUp(self):
        self.hostvars = {
            'stateboard-1': {
                'ansible_host': 'host-1',
                'role_vars': {
                    'stateboard': True,
                },
            },
            'expelled-1': {
                'ansible_host': 'host-1',
                'role_vars': {
                    'expelled': True,
                },
            },
            'instance-1': {
                'ansible_host': 'host-1',
                'role_vars': {},
            },
            'stateboard-2': {
                'ansible_host': 'host-2',
                'role_vars': {
                    'stateboard': True,
                },
            },
            'expelled-2': {
                'ansible_host': 'host-2',
                'role_vars': {
                    'expelled': True,
                },
            },
            'instance-2': {
                'ansible_host': 'host-2',
                'role_vars': {},
            },
        }

    def test_no_instances_in_play_hosts(self):
        res = call_get_one_not_expelled_instance_for_machine(self.hostvars, [
            'expelled-1', 'expelled-2',
        ])
        self.assertFalse(res.failed, res.msg)
        self.assertEqual(len(res.fact), 0)

    def test_stateboard_found(self):
        res = call_get_one_not_expelled_instance_for_machine(self.hostvars, [
            'expelled-1', 'expelled-2', 'stateboard-1', 'stateboard-2',
        ])
        self.assertFalse(res.failed, res.msg)
        self.assertEqual(res.fact, ['stateboard-1', 'stateboard-2'])

    def test_instances_found(self):
        res = call_get_one_not_expelled_instance_for_machine(self.hostvars, [
            'expelled-1', 'expelled-2', 'instance-1', 'instance-2', 'stateboard-1', 'stateboard-2',
        ])
        self.assertFalse(res.failed, res.msg)

        single_instances = res.fact
        self.assertEqual(len(single_instances), 2)
        self.assertTrue('instance-1' in single_instances or 'stateboard-1' in single_instances)
        self.assertTrue('instance-2' in single_instances or 'stateboard-2' in single_instances)
