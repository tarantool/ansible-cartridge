import unittest

from library.cartridge_set_single_instances_for_each_machine import get_one_not_expelled_instance_for_machine


def call_get_one_not_expelled_instance_for_machine(hostvars, play_hosts=None):
    if play_hosts is None:
        play_hosts = hostvars.keys()

    return get_one_not_expelled_instance_for_machine({
        'hostvars': hostvars,
        'play_hosts': play_hosts,
    })


class TestSetOneInstanceForMachine(unittest.TestCase):
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
        self.assertFalse(res.failed, res.msg)
        self.assertEqual(len(res.facts['single_instances_for_each_machine']), 0)

    def test_stateboard_found(self):
        res = call_get_one_not_expelled_instance_for_machine(self.hostvars, [
            'expelled-1', 'expelled-2', 'stateboard-1', 'stateboard-2',
        ])
        self.assertFalse(res.failed, res.msg)
        self.assertEqual(res.facts['single_instances_for_each_machine'], ['stateboard-1', 'stateboard-2'])

    def test_instances_found(self):
        res = call_get_one_not_expelled_instance_for_machine(self.hostvars, [
            'expelled-1', 'expelled-2', 'instance-1', 'instance-2', 'stateboard-1', 'stateboard-2',
        ])
        self.assertFalse(res.failed, res.msg)

        single_instances = res.facts['single_instances_for_each_machine']
        self.assertEqual(len(single_instances), 2)
        self.assertTrue('instance-1' in single_instances or 'stateboard-1' in single_instances)
        self.assertTrue('instance-2' in single_instances or 'stateboard-2' in single_instances)
