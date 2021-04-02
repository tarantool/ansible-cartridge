#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'hostvars': {'required': True, 'type': 'dict'},
}

sets_list = {
    'validate_config': [
        'all_rw',
        'cartridge_app_config',
        'cartridge_app_name',
        'cartridge_auth',
        'cartridge_bootstrap_vshard',
        'cartridge_cluster_cookie',
        'cartridge_conf_dir',
        'cartridge_configure_systemd_unit_files',
        'cartridge_configure_tmpfiles',
        'cartridge_custom_steps',
        'cartridge_custom_steps_dir',
        'cartridge_data_dir',
        'cartridge_defaults',
        'cartridge_enable_tarantool_repo',
        'cartridge_failover',
        'cartridge_failover_params',
        'cartridge_install_dir',
        'cartridge_install_tarantool_for_tgz',
        'cartridge_instances_dir',
        'cartridge_keep_num_latest_dists',
        'cartridge_memtx_dir_parent',
        'cartridge_multiversion',
        'cartridge_package_path',
        'cartridge_remove_temporary_files',
        'cartridge_run_dir',
        'cartridge_scenario',
        'cartridge_systemd_dir',
        'cartridge_tmpfiles_dir',
        'cartridge_vinyl_dir_parent',
        'cartridge_wait_buckets_discovery',
        'cartridge_wal_dir_parent',
        'config',
        'edit_topology_timeout',
        'expelled',
        'failover_priority',
        'instance_discover_buckets_timeout',
        'instance_start_timeout',
        'replicaset_alias',
        'restarted',
        'roles',
        'stateboard',
        'vshard_group',
        'weight',
        'zone',
    ],
    'single_instances_for_each_machine': [
        'expelled',
        'ansible_host',
    ],
    'connect_to_membership': [
        'expelled',
        'stateboard',
        'config',
    ],
    'not_expelled_instance': [
        'expelled',
        'stateboard',
        'instance_info',
    ],
    'control_instance': [
        'expelled',
        'stateboard',
        'config',
        'replicaset_alias',
        'cartridge_run_dir',
    ],
    'edit_topology': [
        'expelled',
        'stateboard',
        'replicaset_alias',
        'roles',
        'failover_priority',
        'all_rw',
        'weight',
        'vshard_group',
        'zone',
        'config',
    ],
}


def get_scenario_steps(params):
    hostvars = params['hostvars']

    facts = {}
    for host_name in hostvars:
        instance_vars = hostvars[host_name]

        for set_name, fact_names in sets_list.items():
            facts[set_name] = facts.get(set_name, {})
            facts[set_name][host_name] = facts[set_name].get(host_name, {})

            for fact_name in fact_names:
                if fact_name in instance_vars:
                    facts[set_name][host_name][fact_name] = instance_vars[fact_name]

    return helpers.ModuleRes(changed=False, facts=facts)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_scenario_steps)
