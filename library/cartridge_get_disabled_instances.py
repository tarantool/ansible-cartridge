#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'module_hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
}


def get_disabled_instances_from_instance_config(instance_vars):
    return instance_vars['instance_info']['disabled_instances']


def get_topology_checksum_from_instance_config(instance_vars):
    return instance_vars['instance_info']['topology_checksum']


def config_mismatched(module_hostvars, instance_name, other_hosts):
    current_checksum = get_topology_checksum_from_instance_config(module_hostvars[instance_name])

    for other_name in other_hosts:
        other_checksum = get_topology_checksum_from_instance_config(module_hostvars[other_name])
        if current_checksum != other_checksum:
            return True

    return False


def count_cluster_disabled_instances(module_hostvars, play_hosts):
    config_mismatch_count = 0
    healthy_count = 0
    votes_to_disable = {}

    play_hosts = list(filter(
        # Disabled instances is None on stateboard and not started instances
        lambda name: all([
            get_disabled_instances_from_instance_config(module_hostvars[name]) is not None,
            get_topology_checksum_from_instance_config(module_hostvars[name]) is not None,
        ]),
        play_hosts,
    ))

    for instance_name in play_hosts:
        disabled_instances = get_disabled_instances_from_instance_config(module_hostvars[instance_name])

        not_disabled_names = list(filter(lambda other_name: other_name not in disabled_instances, play_hosts))
        if config_mismatched(module_hostvars, instance_name, not_disabled_names):
            config_mismatch_count += 1
            continue

        healthy_count += 1
        for disabled_instance in disabled_instances:
            votes_to_disable[disabled_instance] = votes_to_disable.get(disabled_instance, 0) + 1

    if healthy_count == 0 and config_mismatch_count > 0:
        return None, 'All instances in cluster has different topology configs'

    final_disabled_instances = []
    split_brain_suspected = False

    for name, score in votes_to_disable.items():
        if score >= healthy_count / 2:
            final_disabled_instances.append(name)
        if score != healthy_count:
            split_brain_suspected = True

    if split_brain_suspected:
        helpers.warn("It seems that you have split brain in your cluster")

    return sorted(final_disabled_instances), None


def count_inventory_disabled_instances(module_hostvars, play_hosts):
    return sorted(filter(
        lambda name: helpers.is_disabled(module_hostvars[name]),
        play_hosts,
    ))


def count_disabled_instances(params):
    module_hostvars = params['module_hostvars']
    play_hosts = params['play_hosts']

    inventory_disabled_instances = count_inventory_disabled_instances(module_hostvars, play_hosts)

    cluster_disabled_instances, err = count_cluster_disabled_instances(module_hostvars, play_hosts)
    if err:
        return helpers.ModuleRes(failed=True, msg=err)

    return helpers.ModuleRes(changed=False, inventory=inventory_disabled_instances, cluster=cluster_disabled_instances)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, count_disabled_instances)
