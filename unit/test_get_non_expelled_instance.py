import sys
import unittest

import module_utils.helpers as helpers

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_get_not_expelled_instance import get_one_not_expelled_instance


def call_get_one_not_expelled_instance(hostvars, play_hosts=None):
    if play_hosts is None:
        play_hosts = hostvars.keys()

    return get_one_not_expelled_instance({
        'hostvars': hostvars,
        'play_hosts': play_hosts,
    })


class TestGetOneNotExpelledInstance(unittest.TestCase):
    def setUp(self):
        self.hostvars = {
            'expelled-1': {
                'expelled': True,
            },
            'my-stateboard': {
                'stateboard': True,
            },
            'expelled-2': {
                'expelled': True,
            },
            'instance-1': {
                'instance_info': {'console_sock': 'sock-1'},
            },
            'instance-2': {
                'instance_info': {'console_sock': 'sock-2'},
            },
            'instance-3': {
                'instance_info': {'console_sock': 'sock-3'},
            },
        }

    def test_no_instances_in_play_hosts(self):
        res = call_get_one_not_expelled_instance(self.hostvars, [
            'expelled-1', 'my-stateboard', 'expelled-2',
        ])
        self.assertTrue(res.failed)
        self.assertIn('Not found any instance that is not expelled and is not a stateboard', res.msg)

    def test_instance_found(self):
        res = call_get_one_not_expelled_instance(self.hostvars, [
            'expelled-1', 'my-stateboard', 'expelled-2', 'instance-1', 'instance-2', 'instance-3',
        ])
        self.assertFalse(res.failed, res.msg)

        possible_meta = [
            {'name': 'instance-1', 'console_sock': 'sock-1'},
            {'name': 'instance-2', 'console_sock': 'sock-2'},
        ]

        self.assertIn(res.fact, possible_meta)
