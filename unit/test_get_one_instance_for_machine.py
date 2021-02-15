# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import unittest

from library.cartridge_get_instance_from_each_machine import get_one_not_expelled_instance_for_machine


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
                'stateboard': True,
                'ansible_host': 'host-1',
            },
            'expelled-1': {
                'expelled': True,
                'ansible_host': 'host-1',
            },
            'instance-1': {
                'ansible_host': 'host-1',
            },
            'stateboard-2': {
                'stateboard': True,
                'ansible_host': 'host-2',
            },
            'expelled-2': {
                'expelled': True,
                'ansible_host': 'host-2',
            },
            'instance-2': {
                'ansible_host': 'host-2',
            },
        }

    def test_no_instances_in_play_hosts(self):
        res = call_get_one_not_expelled_instance_for_machine(self.hostvars, [
            'expelled-1', 'expelled-2',
        ])
        self.assertTrue(res.success, res.msg)
        self.assertEqual(len(res.meta['names']), 0)

    def test_stateboard_found(self):
        res = call_get_one_not_expelled_instance_for_machine(self.hostvars, [
            'expelled-1', 'expelled-2', 'stateboard-1', 'stateboard-2',
        ])
        self.assertTrue(res.success, res.msg)
        self.assertEqual(res.meta['names'], ['stateboard-1', 'stateboard-2'])

    def test_instances_found(self):
        res = call_get_one_not_expelled_instance_for_machine(self.hostvars, [
            'expelled-1', 'expelled-2', 'instance-1', 'instance-2', 'stateboard-1', 'stateboard-2',
        ])
        self.assertTrue(res.success, res.msg)
        self.assertEqual(res.meta['names'], ['instance-1', 'instance-2'])
