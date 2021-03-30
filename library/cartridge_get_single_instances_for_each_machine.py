#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
}


def get_machine_hostname(instance_vars, instance_name):
    if 'ansible_host' in instance_vars:
        return instance_vars['ansible_host']

    raise Exception('Instance %s has not "ansible_host" option!' % instance_name)


def get_one_not_expelled_instance_for_machine(params):
    hostvars = params['hostvars']
    play_hosts = params['play_hosts']

    machine_hostnames = set()
    instance_names = []

    for instance_name in play_hosts:
        instance_vars = hostvars[instance_name]

        if helpers.is_expelled(instance_vars['role_vars']):
            continue

        machine_hostname = get_machine_hostname(instance_vars, instance_name)
        if machine_hostname not in machine_hostnames:
            machine_hostnames.add(machine_hostname)
            instance_names.append(instance_name)

    return helpers.ModuleRes(changed=False, fact=instance_names)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_one_not_expelled_instance_for_machine)
