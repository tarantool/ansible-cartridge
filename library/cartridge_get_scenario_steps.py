#!/usr/bin/env python

import os

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'role_path': {'required': True, 'type': 'str'},
    'custom_steps_dir': {'required': True, 'type': 'str'},
    'custom_steps': {'required': True, 'type': 'list'},
    'role_scenarios': {'required': True, 'type': 'dict'},
    'custom_scenarios': {'required': True, 'type': 'dict'},
    'scenario_name': {'required': True, 'type': 'str'},
    'scenario': {'required': True, 'type': 'list'},
}


def get_step_name_from_path(path):
    return os.path.splitext(os.path.basename(path))[0]


def get_steps_paths_from_dir(dir_path):
    steps_paths = {}

    if dir_path is None:
        return steps_paths

    file_names = os.listdir(dir_path)
    file_names = filter(lambda x: x.endswith('.yml') or x.endswith('.yaml'), file_names)
    for file_name in file_names:
        name = get_step_name_from_path(file_name)
        steps_paths[name] = os.path.abspath(os.path.join(dir_path, file_name))

    return steps_paths


def get_steps_paths_from_list(steps_list):
    return {
        step.get('name', get_step_name_from_path(step['file'])): os.path.abspath(step['file'])
        for step in steps_list
    }


def get_steps_paths(role_path, custom_steps_dir, custom_steps):
    role_steps_dir = os.path.join(role_path, 'tasks', 'steps')

    role_steps_paths = get_steps_paths_from_dir(role_steps_dir)
    custom_steps_paths_from_dir = get_steps_paths_from_dir(custom_steps_dir)
    custom_steps_paths = get_steps_paths_from_list(custom_steps)

    role_steps = {}
    role_steps.update(role_steps_paths)
    role_steps.update(custom_steps_paths_from_dir)
    role_steps.update(custom_steps_paths)

    return role_steps


def get_scenario(scenario, role_scenarios, custom_scenarios, scenario_name):
    if scenario is None:
        scenarios = role_scenarios.copy()
        scenarios.update(custom_scenarios)
        if scenario_name not in scenarios:
            return None, "Unknown scenario '%s'" % scenario_name
        scenario = scenarios[scenario_name]

    return scenario, None


def get_scenario_steps(params):
    steps_paths = get_steps_paths(params['role_path'], params['custom_steps_dir'], params['custom_steps'])
    scenario, err = get_scenario(
        params['scenario'],
        params['role_scenarios'], params['custom_scenarios'], params['scenario_name'],
    )
    if err:
        return helpers.ModuleRes(failed=True, msg=err)

    scenario_steps = []
    for step_name in scenario:
        if step_name not in steps_paths:
            return helpers.ModuleRes(failed=True, msg="Unknown step '%s'" % step_name)

        scenario_steps.append({
            'name': step_name,
            'path': steps_paths[step_name],
        })

    return helpers.ModuleRes(changed=False, fact=scenario_steps)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_scenario_steps)
