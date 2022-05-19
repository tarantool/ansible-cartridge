import os
import sys
import unittest

import yaml

import module_utils.helpers as helpers

sys.modules['ansible.module_utils.helpers'] = helpers
from filter_plugins.filters import get_cached_facts
from library.cartridge_validate_config import SCHEMA


class TestGetCachedFacts(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

        role_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')

        self.defaults_file = os.path.join(role_dir, 'defaults', 'main.yml')
        with open(self.defaults_file, 'r') as f:
            try:
                self.defaults = yaml.safe_load(f)
                self.cached_fact_names_by_target = self.defaults['cartridge_cached_fact_names_by_target']
            except yaml.YAMLError as e:
                self.fail("Impossible to parse 'defaults/main.yml': %s" % e)

    def test_get_cached_facts(self):
        res = get_cached_facts({
            'instance_1': {
                'expelled': True,
                'config': {'advertise_uri': '10.0.0.1:3001'},
                'ansible_host': 'some_host',
                'cartridge_cluster_cookie': 'some-cookie',
                'cartridge_run_dir': 'some-run-dir',
                'instance_info': {
                    'disabled_instances': [],
                },
            },
            'instance_2': {
                'stateboard': False,
                'random_arg': {'test': 'value'},
                'instance_info': {
                    'disabled_instances': ['instance_2'],
                },
            },
            'instance_3': {
                'disabled': True,
                'random_arg': {'test': 'value'},
                'instance_info': {
                    'disabled_instances': ['instance_2'],
                },
            },
        }, self.cached_fact_names_by_target)
        self.assertEqual(res, {
            'validate_config': {
                'instance_1': {
                    'expelled': True,
                    'config': {'advertise_uri': '10.0.0.1:3001'},
                    'cartridge_cluster_cookie': 'some-cookie',
                    'cartridge_run_dir': 'some-run-dir',
                },
                'instance_2': {
                    'stateboard': False,
                },
                'instance_3': {
                    'disabled': True,
                },
            },
            'count_disabled_instances': {
                'instance_1': {
                    'expelled': True,
                    'instance_info': {
                        'disabled_instances': [],
                    },
                },
                'instance_2': {
                    'instance_info': {
                        'disabled_instances': ['instance_2'],
                    },
                },
                'instance_3': {
                    'disabled': True,
                    'instance_info': {
                        'disabled_instances': ['instance_2'],
                    },
                },
            },
            'facts_for_machines': {
                'instance_1': {
                    'expelled': True,
                    'ansible_host': 'some_host',
                },
                'instance_2': {},
                'instance_3': {
                    'disabled': True,
                },
            },
            'connect_to_membership': {
                'instance_1': {
                    'expelled': True,
                    'config': {'advertise_uri': '10.0.0.1:3001'},
                },
                'instance_2': {
                    'stateboard': False,
                },
                'instance_3': {
                    'disabled': True,
                },
            },
            'alive_not_expelled_instance': {
                'instance_1': {
                    'expelled': True,
                    'config': {'advertise_uri': '10.0.0.1:3001'},
                    'cartridge_run_dir': 'some-run-dir',
                },
                'instance_2': {
                    'stateboard': False,
                },
                'instance_3': {
                    'disabled': True,
                },
            },
            'control_instance': {
                'instance_1': {
                    'expelled': True,
                    'config': {'advertise_uri': '10.0.0.1:3001'},
                    'cartridge_run_dir': 'some-run-dir',
                },
                'instance_2': {
                    'stateboard': False,
                },
                'instance_3': {
                    'disabled': True,
                },
            },
            'edit_topology': {
                'instance_1': {
                    'expelled': True,
                    'config': {'advertise_uri': '10.0.0.1:3001'},
                },
                'instance_2': {
                    'stateboard': False,
                },
                'instance_3': {
                    'disabled': True,
                },
            },
            'failover_promote': {
                'instance_1': {'expelled': True},
                'instance_2': {'stateboard': False},
                'instance_3': {
                    'disabled': True,
                },
            },
        })

    def test_validate_config_cached_facts(self):
        self.assertEqual(sorted(SCHEMA.keys()), sorted(self.cached_fact_names_by_target['validate_config']))
