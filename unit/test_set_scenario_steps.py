import os
import sys
import unittest

import module_utils.helpers as helpers

sys.modules['ansible.module_utils.helpers'] = helpers

from library.cartridge_set_scenario_steps import get_scenario_steps


class TestSetSteps(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

        self.role_path = '/role'
        self.full_role_path = os.path.join(self.role_path, 'tasks', 'steps')
        self.custom_steps_dir = '/custom_steps_dir'
        self.dirs = {
            self.full_role_path: {
                'task_1.yml',
                'task_2.yaml',
                'task_3.yml',
            },
            self.custom_steps_dir: {
                'task_2.yaml',
                'task_4.yml',
                'task_5.yml',
            },
        }

        def test_listdir(path):
            return self.dirs.get(path)

        self.original_listdir = os.listdir
        os.listdir = test_listdir

    @staticmethod
    def call_get_tasks_paths(scenario, role_path, custom_steps_dir=None, custom_steps=None):
        return get_scenario_steps({
            'scenario': scenario,
            'role_path': role_path,
            'custom_steps_dir': custom_steps_dir,
            'custom_steps': custom_steps,
        })

    def test_role_path(self):
        tasks = self.call_get_tasks_paths(
            scenario=['task_1', 'task_2', 'task_3'],
            role_path=self.role_path,
        )
        self.assertEqual(tasks.facts['scenario_steps'], [
            {'name': 'task_1', 'path': os.path.join(self.full_role_path, 'task_1.yml')},
            {'name': 'task_2', 'path': os.path.join(self.full_role_path, 'task_2.yaml')},
            {'name': 'task_3', 'path': os.path.join(self.full_role_path, 'task_3.yml')},
        ])

    def test_custom_steps_dir(self):
        tasks = self.call_get_tasks_paths(
            scenario=['task_1', 'task_2', 'task_3', 'task_4', 'task_5'],
            role_path=self.role_path,
            custom_steps_dir=self.custom_steps_dir,
        )
        self.assertEqual(tasks.facts['scenario_steps'], [
            {'name': 'task_1', 'path': os.path.join(self.full_role_path, 'task_1.yml')},
            {'name': 'task_2', 'path': os.path.join(self.custom_steps_dir, 'task_2.yaml')},
            {'name': 'task_3', 'path': os.path.join(self.full_role_path, 'task_3.yml')},
            {'name': 'task_4', 'path': os.path.join(self.custom_steps_dir, 'task_4.yml')},
            {'name': 'task_5', 'path': os.path.join(self.custom_steps_dir, 'task_5.yml')},
        ])

    def test_custom_steps(self):
        tasks = self.call_get_tasks_paths(
            scenario=['task_1', 'task_2', 'task_3', 'task_5', 'task_6'],
            role_path=self.role_path,
            custom_steps=[
                {'name': 'task_3', 'file': '/custom_steps/task_3.yml'},
                {'name': 'task_5', 'file': '/custom_steps/task_5.yml'},
                {'name': 'task_6', 'file': '/custom_steps/task_6.yml'},
            ],
        )
        self.assertEqual(tasks.facts['scenario_steps'], [
            {'name': 'task_1', 'path': os.path.join(self.full_role_path, 'task_1.yml')},
            {'name': 'task_2', 'path': os.path.join(self.full_role_path, 'task_2.yaml')},
            {'name': 'task_3', 'path': '/custom_steps/task_3.yml'},
            {'name': 'task_5', 'path': '/custom_steps/task_5.yml'},
            {'name': 'task_6', 'path': '/custom_steps/task_6.yml'},
        ])

    def test_all(self):
        tasks = self.call_get_tasks_paths(
            scenario=['task_1', 'task_2', 'task_3', 'task_4', 'task_5', 'task_6'],
            role_path=self.role_path,
            custom_steps_dir=self.custom_steps_dir,
            custom_steps=[
                {'name': 'task_3', 'file': '/custom_steps/task_3.yml'},
                {'name': 'task_5', 'file': '/custom_steps/task_5.yml'},
                {'name': 'task_6', 'file': '/custom_steps/task_6.yml'},
            ],
        )
        self.assertEqual(tasks.facts['scenario_steps'], [
            {'name': 'task_1', 'path': os.path.join(self.full_role_path, 'task_1.yml')},
            {'name': 'task_2', 'path': os.path.join(self.custom_steps_dir, 'task_2.yaml')},
            {'name': 'task_3', 'path': '/custom_steps/task_3.yml'},
            {'name': 'task_4', 'path': os.path.join(self.custom_steps_dir, 'task_4.yml')},
            {'name': 'task_5', 'path': '/custom_steps/task_5.yml'},
            {'name': 'task_6', 'path': '/custom_steps/task_6.yml'},
        ])

    def test_rewrite(self):
        tasks = self.call_get_tasks_paths(
            scenario=['task_2'],
            role_path=self.role_path,
        )
        self.assertEqual(tasks.facts['scenario_steps'], [
            {'name': 'task_2', 'path': os.path.join(self.full_role_path, 'task_2.yaml')},
        ])

        tasks = self.call_get_tasks_paths(
            scenario=['task_2'],
            role_path=self.role_path,
            custom_steps_dir=self.custom_steps_dir,
        )
        self.assertEqual(tasks.facts['scenario_steps'], [
            {'name': 'task_2', 'path': os.path.join(self.custom_steps_dir, 'task_2.yaml')},
        ])

        tasks = self.call_get_tasks_paths(
            scenario=['task_2'],
            role_path=self.role_path,
            custom_steps_dir=self.custom_steps_dir,
            custom_steps=[
                {'name': 'task_2', 'file': '/custom_steps/task_2.yaml'},
            ],
        )
        self.assertEqual(tasks.facts['scenario_steps'], [
            {'name': 'task_2', 'path': '/custom_steps/task_2.yaml'},
        ])

    def test_task_not_found(self):
        res = self.call_get_tasks_paths(
            scenario=['unknown_task'],
            role_path=self.role_path,
        )
        self.assertEqual(res.msg, "Unknown step 'unknown_task'")

    def tearDown(self):
        os.listdir = self.original_listdir
