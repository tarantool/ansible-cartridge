import sys
import unittest

import module_utils.helpers as helpers

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_get_single_instances_for_each_machine import get_one_not_expelled_instance_for_machine


def call_get_one_not_expelled_instance_for_machine(module_hostvars, play_hosts=None):
    if play_hosts is None:
        play_hosts = module_hostvars.keys()

    return get_one_not_expelled_instance_for_machine({
        'module_hostvars': module_hostvars,
        'play_hosts': play_hosts,
    })


class TestGetOneInstanceForMachine(unittest.TestCase):
    def setUp(self):
        self.hostvars = {
            'stateboard-1': {
                'ansible_host': 'host-1',
                'stateboard': True,
            },
            'expelled-1': {
                'ansible_host': 'host-1',
                'expelled': True,
            },
            'instance-1-1': {
                'ansible_host': 'host-1',
            },
            'instance-1-2': {
                'ansible_host': 'host-1',
                'ansible_port': 22,
            },
            'instance-1-3': {
                'ansible_host': 'host-1',
                'ansible_port': 33,  # different port
            },
            'instance-1-4': {
                'ansible_host': 'host-1',
                'ansible_port': 33,  # different port
            },
            'stateboard-2': {
                'ansible_host': 'host-2',
                'stateboard': True,
            },
            'expelled-2': {
                'ansible_host': 'host-2',
                'expelled': True,
            },
            'instance-2-1': {
                'ansible_host': 'host-2',
            },
            'instance-2-2': {
                'ansible_host': 'host-2',
                'ansible_port': 22,
            },
            'instance-2-3': {
                'ansible_host': 'host-2',
                'ansible_port': 33,  # different port
            },
            'instance-2-4': {
                'ansible_host': 'host-2',
                'ansible_port': 44,  # one more different port
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

    def test_all_instances_specified(self):
        res = call_get_one_not_expelled_instance_for_machine(self.hostvars, [
            'expelled-1', 'expelled-2',
            'stateboard-1', 'stateboard-2',
            'instance-1-1', 'instance-1-2', 'instance-1-3', 'instance-1-4',
            'instance-2-1', 'instance-2-2', 'instance-2-3', 'instance-2-4',
        ])
        self.assertFalse(res.failed, res.msg)

        single_instances = res.fact
        self.assertSetEqual(set(single_instances), {
            'instance-1-1', 'instance-1-3',
            'instance-2-1', 'instance-2-3', 'instance-2-4',
        })
