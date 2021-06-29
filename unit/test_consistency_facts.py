import os
import re
import unittest

import yaml


# This tests protects against inattentive people, who do not completely change the variables list

class TestConsistencyFacts(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

        role_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')

        self.defaults_file = os.path.join(role_dir, 'defaults', 'main.yml')
        with open(self.defaults_file, 'r') as f:
            try:
                self.defaults = yaml.safe_load(f)
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

    # If someone added a variable to defaults, but forgot to set it in 'set_instance_facts' step
    def test_set_instance_facts(self):
        default_names = list(self.defaults.keys())
        set_instance_facts_name = list(self.set_instance_facts[0]['set_fact']['role_facts'].keys())

        self.assertEqual(
            default_names, set_instance_facts_name,
            'List of facts in defaults and in "set_instance_fact" step is different',
        )

    # If someone added a variable to defaults, but forgot to add it to doc
    def test_doc_facts(self):
        default_names = list(self.defaults.keys())
        undocumented_facts = [
            # Role defaults
            'cartridge_role_scenarios',
            # Cross-step facts
            'delivered_package_path',
            'control_instance',
            'temporary_files',
            'needs_restart',
            'alive_not_expelled_instance',
            # Temp facts
            'cached_facts_res',
            'cached_facts',
            'single_instances_for_each_machine_res',
            'single_instances_for_each_machine',
        ]

        self.assertEqual(
            sorted(default_names), sorted(self.doc_facts + undocumented_facts),
            'List of facts in defaults and in documentation is different',
        )
