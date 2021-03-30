import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
import unittest

from library.cartridge_get_scenario_steps import get_scenario_steps


class TestGetSteps(unittest.TestCase):
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

    def call_get_tasks_paths(
        self,
        scenario=None,
        custom_steps_dir=None,
        custom_steps=None,
        role_scenarios=None,
        custom_scenarios=None,
        scenario_name='default',
    ):
        custom_steps = custom_steps or []
        role_scenarios = role_scenarios or {
            'default': ['task_1', 'task_2']
        }
        custom_scenarios = custom_scenarios or {}

        return get_scenario_steps({
            'role_path': self.role_path,
            'custom_steps_dir': custom_steps_dir,
            'custom_steps': custom_steps,
            'role_scenarios': role_scenarios,
            'custom_scenarios': custom_scenarios,
            'scenario_name': scenario_name,
            'scenario': scenario,
        })

    def test_role_path(self):
        tasks = self.call_get_tasks_paths(
            scenario=['task_1', 'task_2', 'task_3'],
        )
        self.assertEqual(tasks.fact, [
            {'name': 'task_1', 'path': os.path.join(self.full_role_path, 'task_1.yml')},
            {'name': 'task_2', 'path': os.path.join(self.full_role_path, 'task_2.yaml')},
            {'name': 'task_3', 'path': os.path.join(self.full_role_path, 'task_3.yml')},
        ])

    def test_custom_steps_dir(self):
        tasks = self.call_get_tasks_paths(
            scenario=['task_1', 'task_2', 'task_3', 'task_4', 'task_5'],
            custom_steps_dir=self.custom_steps_dir,
        )
        self.assertEqual(tasks.fact, [
            {'name': 'task_1', 'path': os.path.join(self.full_role_path, 'task_1.yml')},
            {'name': 'task_2', 'path': os.path.join(self.custom_steps_dir, 'task_2.yaml')},
            {'name': 'task_3', 'path': os.path.join(self.full_role_path, 'task_3.yml')},
            {'name': 'task_4', 'path': os.path.join(self.custom_steps_dir, 'task_4.yml')},
            {'name': 'task_5', 'path': os.path.join(self.custom_steps_dir, 'task_5.yml')},
        ])

    def test_custom_steps(self):
        tasks = self.call_get_tasks_paths(
            scenario=['task_1', 'task_2', 'task_3', 'task_5', 'task_6'],
            custom_steps=[
                {'name': 'task_3', 'file': '/custom_steps/task_3.yml'},
                {'name': 'task_5', 'file': '/custom_steps/task_5.yml'},
                {'name': 'task_6', 'file': '/custom_steps/task_6.yml'},
            ],
        )
        self.assertEqual(tasks.fact, [
            {'name': 'task_1', 'path': os.path.join(self.full_role_path, 'task_1.yml')},
            {'name': 'task_2', 'path': os.path.join(self.full_role_path, 'task_2.yaml')},
            {'name': 'task_3', 'path': '/custom_steps/task_3.yml'},
            {'name': 'task_5', 'path': '/custom_steps/task_5.yml'},
            {'name': 'task_6', 'path': '/custom_steps/task_6.yml'},
        ])

    def test_all(self):
        tasks = self.call_get_tasks_paths(
            scenario=['task_1', 'task_2', 'task_3', 'task_4', 'task_5', 'task_6'],
            custom_steps_dir=self.custom_steps_dir,
            custom_steps=[
                {'name': 'task_3', 'file': '/custom_steps/task_3.yml'},
                {'name': 'task_5', 'file': '/custom_steps/task_5.yml'},
                {'name': 'task_6', 'file': '/custom_steps/task_6.yml'},
            ],
        )
        self.assertEqual(tasks.fact, [
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
        )
        self.assertEqual(tasks.fact, [
            {'name': 'task_2', 'path': os.path.join(self.full_role_path, 'task_2.yaml')},
        ])

        tasks = self.call_get_tasks_paths(
            scenario=['task_2'],
            custom_steps_dir=self.custom_steps_dir,
        )
        self.assertEqual(tasks.fact, [
            {'name': 'task_2', 'path': os.path.join(self.custom_steps_dir, 'task_2.yaml')},
        ])

        tasks = self.call_get_tasks_paths(
            scenario=['task_2'],
            custom_steps_dir=self.custom_steps_dir,
            custom_steps=[
                {'name': 'task_2', 'file': '/custom_steps/task_2.yaml'},
            ],
        )
        self.assertEqual(tasks.fact, [
            {'name': 'task_2', 'path': '/custom_steps/task_2.yaml'},
        ])

    def test_task_not_found(self):
        res = self.call_get_tasks_paths(
            scenario=['unknown_task'],
        )
        self.assertEqual(res.msg, "Unknown step 'unknown_task'")

    def test_default_role_scenario(self):
        tasks = self.call_get_tasks_paths()
        self.assertEqual(tasks.fact, [
            {'name': 'task_1', 'path': os.path.join(self.full_role_path, 'task_1.yml')},
            {'name': 'task_2', 'path': os.path.join(self.full_role_path, 'task_2.yaml')},
        ])

    def test_unknown_scenario_name(self):
        res = self.call_get_tasks_paths(
            scenario_name='unknown_scenario'
        )
        self.assertEqual(res.msg, "Unknown scenario 'unknown_scenario'")

    def test_custom_scenarios(self):
        role_scenarios = {
            'default_1': ['task_1'],
            'default_2': ['task_2'],
        }
        custom_scenarios = {
            'default_2': ['task_3'],
            'custom_1': ['task_1', 'task_2'],
        }

        tasks = self.call_get_tasks_paths(
            scenario_name='default_1',
            role_scenarios=role_scenarios,
            custom_scenarios=custom_scenarios,
        )
        self.assertEqual(tasks.fact, [
            {'name': 'task_1', 'path': os.path.join(self.full_role_path, 'task_1.yml')},
        ])

        tasks = self.call_get_tasks_paths(
            scenario_name='default_2',
            role_scenarios=role_scenarios,
            custom_scenarios=custom_scenarios,
        )
        self.assertEqual(tasks.fact, [
            {'name': 'task_3', 'path': os.path.join(self.full_role_path, 'task_3.yml')},
        ])

        tasks = self.call_get_tasks_paths(
            scenario_name='custom_1',
            role_scenarios=role_scenarios,
            custom_scenarios=custom_scenarios,
        )
        self.assertEqual(tasks.fact, [
            {'name': 'task_1', 'path': os.path.join(self.full_role_path, 'task_1.yml')},
            {'name': 'task_2', 'path': os.path.join(self.full_role_path, 'task_2.yaml')},
        ])

    def test_scenario_priority(self):
        role_scenarios = {
            'default_1': ['task_1'],
        }
        custom_scenarios = {
            'custom_1': ['task_2'],
        }

        tasks = self.call_get_tasks_paths(
            scenario_name='default_1',
            role_scenarios=role_scenarios,
            custom_scenarios=custom_scenarios,
            scenario=['task_3']
        )
        self.assertEqual(tasks.fact, [
            {'name': 'task_3', 'path': os.path.join(self.full_role_path, 'task_3.yml')},
        ])

        tasks = self.call_get_tasks_paths(
            scenario_name='custom_1',
            role_scenarios=role_scenarios,
            custom_scenarios=custom_scenarios,
            scenario=['task_3']
        )
        self.assertEqual(tasks.fact, [
            {'name': 'task_3', 'path': os.path.join(self.full_role_path, 'task_3.yml')},
        ])

    def tearDown(self):
        os.listdir = self.original_listdir
