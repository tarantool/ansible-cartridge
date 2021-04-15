import os
import unittest
import yaml


class TestSetInstanceFacts(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

        role_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')

        self.defaults_file = os.path.join(role_dir, 'defaults', 'main.yml')
        with open(self.defaults_file, 'r') as f:
            try:
                self.defaults = yaml.safe_load(f)
            except yaml.YAMLError as e:
                self.fail("Impossible to parse 'set_instance_facts.yml': %s" % e)

        self.set_instance_facts_file = os.path.join(role_dir, 'tasks', 'set_instance_facts.yml')
        with open(self.set_instance_facts_file, 'r') as f:
            try:
                self.set_instance_facts = yaml.safe_load(f)
            except yaml.YAMLError as e:
                self.fail("Impossible to parse 'set_instance_facts.yml': %s" % e)

    # This test protects against inattentive people, who do not completely change the variables list
    # (if someone added a variable to defaults, but forgot to set it in 'set_instance_facts' step)
    def test_set_instance_facts(self):
        default_names = list(self.defaults.keys())
        set_instance_facts_name = list(self.set_instance_facts[0]['set_fact']['role_facts'].keys())

        self.assertEqual(default_names, set_instance_facts_name)
