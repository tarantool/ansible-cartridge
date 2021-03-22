import os
import pkgutil

if pkgutil.find_loader('ansible.module_utils.helpers'):
    import ansible.module_utils.helpers as helpers
else:
    import module_utils.helpers as helpers

argument_spec = {
    'scenario_steps_names': {'required': True, 'type': 'list'},
    'role_path': {'required': True, 'type': 'str'},
    'custom_steps_dir': {'required': True, 'type': 'str'},
    'custom_steps': {'required': True, 'type': 'list'},
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


def get_scenario_steps(params):
    role_steps_dir = os.path.join(params['role_path'], 'tasks', 'steps')

    role_steps = get_steps_paths_from_dir(role_steps_dir)
    custom_steps_from_dir = get_steps_paths_from_dir(params['custom_steps_dir'])
    custom_steps = get_steps_paths_from_list(params['custom_steps'] or [])

    steps_paths = {
        **role_steps,
        **custom_steps_from_dir,
        **custom_steps,
    }

    scenario_steps = []
    for step_name in params['scenario_steps_names']:
        if step_name not in steps_paths:
            return helpers.ModuleRes(failed=True, msg=f"Unknown step '{step_name}'")

        scenario_steps.append({
            'name': step_name,
            'path': steps_paths[step_name],
        })

    return helpers.ModuleRes(changed=False, facts={
        'scenario_steps': scenario_steps,
    })


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_scenario_steps)
