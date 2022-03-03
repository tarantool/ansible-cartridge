import os
import re
import sys
import unittest

import yaml

import module_utils.helpers as helpers

sys.modules['ansible.module_utils.helpers'] = helpers
import library.cartridge_validate_config as validate_config
import unit.test_validate_config as test_validate_config


# This tests protects against inattentive people, who do not completely change the variables list

class TestFacts(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

        role_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')

        self.defaults_file = os.path.join(role_dir, 'defaults', 'main.yml')
        with open(self.defaults_file, 'r') as f:
            try:
                self.defaults = yaml.safe_load(f)
                self.cached_facts_names = self.defaults['cartridge_cached_fact_names_by_target']
            except yaml.YAMLError as e:
                self.fail("Impossible to parse 'defaults/main.yml': %s" % e)

        self.set_instance_facts_file = os.path.join(role_dir, 'tasks', 'set_instance_facts.yml')
        with open(self.set_instance_facts_file, 'r') as f:
            try:
                self.set_instance_facts = yaml.safe_load(f)
            except yaml.YAMLError as e:
                self.fail("Impossible to parse 'tasks/set_instance_facts.yml': %s" % e)

        self.doc_facts_file = os.path.join(role_dir, 'doc', 'variables.md')
        with open(self.doc_facts_file, 'r') as f:
            text = f.read()
            self.doc_facts = re.findall(r'\n[*-][^`]*`([^`]+)`', text)

        self.validate_config_facts = list(validate_config.SCHEMA.keys())

        self.test_validate_config_facts = set()
        for params in test_validate_config.PARAMS_BY_TYPES.values():
            for param in params:
                self.test_validate_config_facts.add(param.split('.')[0].split('[')[0])
        self.test_validate_config_facts = list(self.test_validate_config_facts)

        self.not_user_facts = [
            # Role defaults
            'cartridge_role_scenarios',
            'cartridge_cached_fact_names_by_target',
            # Cross-step facts
            'delivered_package_path',
            'control_instance',
            'temporary_files',
            'needs_restart',
            'cluster_disabled_instances',
            'inventory_disabled_instances',
            'alive_not_expelled_instance',
            'instance_backup_files',
            'backup_archive_path',
            'fetched_backup_archive_path',
            'backup_files_from_machine',
            # Temp facts
            'cached_facts',
            'facts_for_machines_res',
            'single_instances_for_each_machine',
            'instances_from_same_machine',
        ]

    # If someone added a variable to defaults, but forgot to set it in 'set_instance_facts' step
    def test_set_instance_facts(self):
        default_names = list(self.defaults.keys())
        set_instance_facts_name = list(self.set_instance_facts[0]['set_fact']['role_facts'].keys())

        self.assertEqual(
            sorted(default_names), sorted(set_instance_facts_name + self.not_user_facts),
            'List of facts in defaults and in "set_instance_fact" step is different',
        )

    # If someone added a variable to defaults, but forgot to add it to doc
    def test_doc_facts(self):
        default_names = list(self.defaults.keys())

        self.assertEqual(
            sorted(default_names), sorted(self.doc_facts + self.not_user_facts),
            'List of facts in defaults and in documentation is different',
        )

    # If someone added a variable to defaults, but forgot to add it to validate config
    def test_validate_config_facts(self):
        default_names = list(self.defaults.keys())

        self.assertEqual(
            sorted(default_names), sorted(self.validate_config_facts + self.not_user_facts),
            'List of facts in defaults and in validate config step is different',
        )

    # If someone added a variable to validate config step, but forgot to add it to cached facts list
    def test_validate_config_cached_facts(self):
        cached_facts_names = self.cached_facts_names['validate_config']

        self.assertEqual(
            sorted(self.validate_config_facts), sorted(cached_facts_names),
            'List of facts in cached facts and in validate config step is different',
        )

    # If someone added a variable to validate config step, but forgot to add it to test of validate config
    def test_validate_config_test_facts(self):
        self.assertEqual(
            sorted(self.validate_config_facts), sorted(self.test_validate_config_facts),
            'List of facts in validate config step and in test of this step is different',
        )
