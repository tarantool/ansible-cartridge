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


def get_facts_for_each_machine(params):
    module_hostvars = params['module_hostvars']
    play_hosts = params['play_hosts']

    machines_single_instance = {}
    machines_play_hosts = {}
    instances_play_hosts = {}

    for instance_name in sorted(play_hosts):
        instance_vars = module_hostvars[instance_name]
        machine_id = get_machine_id(instance_vars, instance_name)

        # Calculate play hosts for each machine
        machines_play_hosts[machine_id] = machines_play_hosts.get(machine_id, [])
        machines_play_hosts[machine_id].append(instance_name)

        # Copy link to machine list
        instances_play_hosts[instance_name] = machines_play_hosts[machine_id]

        # Calculate single not expelled instance for each machine
        if all([
            not helpers.is_expelled(instance_vars),
            machine_id not in machines_single_instance,
        ]):
            machines_single_instance[machine_id] = instance_name

    return helpers.ModuleRes(
        changed=False,
        single_instances=list(machines_single_instance.values()),
        play_hosts=instances_play_hosts,
    )


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_facts_for_each_machine)
