#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'module_hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
}


def get_machine_id(instance_vars, instance_name):
    if 'ansible_host' not in instance_vars:
        raise Exception('Instance %s has not "ansible_host" option!' % instance_name)

    machine_id = '%s:%s' % (
        instance_vars['ansible_host'],
        instance_vars.get('ansible_port', 22)
    )

    return machine_id


def get_one_not_expelled_instance_for_machine(params):
    module_hostvars = params['module_hostvars']
    play_hosts = params['play_hosts']

    machine_ids = set()
    instance_names = []

    for instance_name in sorted(play_hosts):
        instance_vars = module_hostvars[instance_name]

        if helpers.is_expelled(instance_vars):
            continue

        machine_id = get_machine_id(instance_vars, instance_name)
        if machine_id not in machine_ids:
            machine_ids.add(machine_id)
            instance_names.append(instance_name)

    return helpers.ModuleRes(changed=False, fact=instance_names)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_one_not_expelled_instance_for_machine)
