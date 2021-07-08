import glob
import os
import re
import unittest


# This test protects against inattentive people, who do not completely change the step list

class TestSteps(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

        role_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')

        self.steps_dir = os.path.join(role_dir, 'tasks', 'steps')
        self.steps = sorted([
            os.path.basename(f)[:-4]
            for f in os.listdir(self.steps_dir)
            if os.path.isfile(os.path.join(self.steps_dir, f))
        ])

        self.entry_points_dir = os.path.join(role_dir, 'tasks')
        self.entry_points = sorted([
            os.path.basename(f)[5:-4]
            for f in glob.glob(os.path.join(self.entry_points_dir, 'step_*'))
        ])

        self.doc_facts_file = os.path.join(role_dir, 'doc', 'steps.md')
        with open(self.doc_facts_file, 'r') as f:
            text = f.read()
            begin = text.find('# Role Steps List')
            end = text.find('# Role Steps Description')
            text = text[begin:end]
            self.doc_facts = re.findall(r'\n[*-][^\[]*\[([^]]+)]', text)

    # If someone added a step to the folder, but forgot to make an entry point for it or vice versa
    def test_steps_entry_points(self):
        self.assertEqual(
            self.steps, self.entry_points,
            'List of steps and entry points is different',
        )

    # If someone added a step to the folder, but forgot to add it to scenario doc
    def test_scenario_doc(self):
        self.assertEqual(
            sorted(self.steps), sorted(self.doc_facts),
            'List of steps and documented steps is different',
        )
