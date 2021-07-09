#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'module_hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
}


def get_disabled_instances(instance_vars):
    return instance_vars['instance_info']['cluster_disabled_instances']


def get_topology_checksum(instance_vars):
    return instance_vars['instance_info']['cluster_topology_checksum']


def check_config_mismatch(module_hostvars, instance_name, other_hosts):
    current_checksum = get_topology_checksum(module_hostvars[instance_name])

    for other_name in other_hosts:
        other_checksum = get_topology_checksum(module_hostvars[other_name])
        if current_checksum != other_checksum:
            return True

    return False


def count_disabled_instances(params):
    module_hostvars = params['module_hostvars']
    play_hosts = params['play_hosts']

    config_mismatch_count = 0
    started_count = 0
    rating = {}

    play_hosts = list(filter(
        # Disabled instances is None on stateboard and not started instances
        lambda name: all([
            get_disabled_instances(module_hostvars[name]) is not None,
            get_topology_checksum(module_hostvars[name]) is not None,
        ]),
        play_hosts,
    ))

    for instance_name in play_hosts:
        disabled_instances = get_disabled_instances(module_hostvars[instance_name])

        not_disabled_names = list(filter(lambda other_name: other_name not in disabled_instances, play_hosts))
        if check_config_mismatch(module_hostvars, instance_name, not_disabled_names):
            config_mismatch_count += 1
            continue

        started_count += 1
        for disabled_instance in disabled_instances:
            rating[disabled_instance] = rating.get(disabled_instance, 0) + 1

    if started_count == 0 and config_mismatch_count > 0:
        return helpers.ModuleRes(failed=True, msg='All instances in cluster has different topology configs')

    final_disabled_instances = []
    split_brain_exists = False

    for name, score in rating.items():
        if score >= started_count / 2:
            final_disabled_instances.append(name)
        if score != started_count:
            split_brain_exists = True

    if split_brain_exists:
        helpers.warn("It seems that you have split brain in your cluster")

    return helpers.ModuleRes(changed=False, fact=sorted(final_disabled_instances))


if __name__ == '__main__':
    helpers.execute_module(argument_spec, count_disabled_instances)
