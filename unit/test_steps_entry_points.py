import glob
import os
import unittest


class TestStepsEntryPoints(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

        role_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
        self.entry_points_dir = os.path.join(role_dir, 'tasks')
        self.steps_dir = os.path.join(role_dir, 'tasks', 'steps')

    # This test protects against inattentive people, who do not completely change the step list
    # (if someone added a step to the folder, but forgot to make an entry point for it or vice versa)
    def test_steps_entry_points(self):
        entry_points = sorted([
            os.path.basename(f)[5:-4]
            for f in glob.glob(os.path.join(self.entry_points_dir, 'step_*'))
        ])
        steps = sorted([
            os.path.basename(f)[:-4]
            for f in os.listdir(self.steps_dir)
            if os.path.isfile(os.path.join(self.steps_dir, f))
        ])

        self.assertEqual(steps, entry_points, 'List of steps and entry points is different')
