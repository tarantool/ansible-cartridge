import sys
import unittest

import module_utils.helpers as helpers

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_get_cached_facts import get_cached_facts, FACTS_BY_TARGETS
from library.cartridge_validate_config import SCHEMA


def call_get_cached_facts(hostvars):
    return get_cached_facts({
        'hostvars': hostvars,
    })


class TestGetCachedFacts(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_get_cached_facts(self):
        res = call_get_cached_facts({
            'instance_1': {
                'expelled': True,
                'config': {'advertise_uri': '10.0.0.1:3001'},
                'ansible_host': 'some_host',
            },
            'instance_2': {
                'stateboard': False,
                'random_arg': {'test': 'value'},
            },
            'instance_3': {
                'random_arg': {'test': 'value'},
            },
        })
        self.assertFalse(res.failed, res.msg)
        self.assertTrue('facts' in res.kwargs, 'No facts in result!')
        self.assertEqual(res.kwargs['facts'], {
            'validate_config': {
                'instance_1': {
                    'expelled': True,
                    'config': {'advertise_uri': '10.0.0.1:3001'},
                },
                'instance_2': {
                    'stateboard': False,
                },
                'instance_3': {},
            },
            'single_instances_for_each_machine': {
                'instance_1': {
                    'expelled': True,
                    'ansible_host': 'some_host',
                },
                'instance_2': {},
                'instance_3': {},
            },
            'connect_to_membership': {
                'instance_1': {
                    'expelled': True,
                    'config': {'advertise_uri': '10.0.0.1:3001'},
                },
                'instance_2': {
                    'stateboard': False,
                },
                'instance_3': {},
            },
            'not_expelled_instance': {
                'instance_1': {
                    'expelled': True,
                },
                'instance_2': {
                    'stateboard': False,
                },
                'instance_3': {},
            },
            'control_instance': {
                'instance_1': {
                    'expelled': True,
                    'config': {'advertise_uri': '10.0.0.1:3001'},
                },
                'instance_2': {
                    'stateboard': False,
                },
                'instance_3': {},
            },
            'edit_topology': {
                'instance_1': {
                    'expelled': True,
                    'config': {'advertise_uri': '10.0.0.1:3001'},
                },
                'instance_2': {
                    'stateboard': False,
                },
                'instance_3': {},
            },
        })

    def test_validate_config_cached_facts(self):
        self.assertEqual(sorted(SCHEMA.keys()), sorted(FACTS_BY_TARGETS['validate_config']))
