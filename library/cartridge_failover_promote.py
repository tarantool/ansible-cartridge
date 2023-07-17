#!/usr/bin/python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'promote_play_hosts': {'required': True, 'type': 'bool'},
    'module_hostvars': {'required': False, 'type': 'dict'},
    'cluster_disabled_instances': {'required': False, 'type': 'list'},
    'play_hosts': {'required': False, 'type': 'list'},

    'console_sock': {'required': True, 'type': 'str'},
    'failover_promote_params': {'required': False, 'type': 'dict'},

    'netbox_call_timeout': {'required': False, 'type': 'int'},
    'upload_config_timeout': {'required': False, 'type': 'int'},
    'apply_config_timeout': {'required': False, 'type': 'int'},
    'validate_config_timeout': {'required': False, 'type': 'int'},
}


def check_leaders_promotion_is_possible(control_console):
    failover_mode, _ = control_console.eval_res_err('''
        local cartridge = require('cartridge')
        if cartridge.failover_get_params == nil then
            return nil
        end

        local failover_params = cartridge.failover_get_params()
        return failover_params.mode
    ''')

    if failover_mode != 'stateful':
        return "Leaders promotion is possible only when stateful failover is enabled"

    return None


def call_failover_promote(control_console, replicaset_leaders, force_inconsistency):
    opts = {
        'force_inconsistency': force_inconsistency,
    }
    return control_console.eval_res_err('''
        return require('cartridge').failover_promote(...)
    ''', replicaset_leaders, opts)


def get_replicaset_leaders_by_play_hosts(play_hosts, module_hostvars, cluster_disabled_instances, control_console):
    cluster_instances = helpers.get_cluster_instances_with_replicasets_info(control_console)

    dead_replicasets = set()
    chosen_leaders_priority = {}  # replicaset uuid: leader priority

    replicaset_leaders = {}
    for instance_name in play_hosts:
        instance_vars = module_hostvars[instance_name]

        if any([
            helpers.is_stateboard(instance_vars),
            not helpers.is_enabled(instance_vars),
            instance_name in cluster_disabled_instances,
        ]):
            continue

        cluster_instance = cluster_instances.get(instance_name)
        if cluster_instance is None:
            continue

        instance_uuid = cluster_instance.get('uuid')
        if not instance_uuid:
            continue

        replicaset_uuid = cluster_instance.get('replicaset_uuid')
        if replicaset_uuid is None:
            continue

        replicaset_alias = cluster_instance.get('replicaset_alias', replicaset_uuid)

        if cluster_instance.get('status') != 'healthy':
            if replicaset_uuid not in replicaset_leaders:
                # there is no alive instances found for this replicaset
                dead_replicasets.add(replicaset_alias)
            continue

        if chosen_leaders_priority.get(replicaset_uuid) is not None:
            if cluster_instance['priority'] > chosen_leaders_priority[replicaset_uuid]:
                # leader with less priority was already chosen
                continue

        replicaset_leaders[replicaset_uuid] = instance_uuid
        chosen_leaders_priority[replicaset_uuid] = cluster_instance['priority']
        dead_replicasets.discard(replicaset_alias)

    return replicaset_leaders, dead_replicasets


def get_replicaset_leaders_by_aliases(specified_replicaset_leaders, control_console):
    if not specified_replicaset_leaders:
        return {}, None

    cluster_instances = helpers.get_cluster_instances(control_console)
    cluster_replicasets = helpers.get_cluster_replicasets(control_console)

    replicaset_leaders = {}
    for replicaset_alias, leader_alias in specified_replicaset_leaders.items():
        cluster_replicaset = cluster_replicasets.get(replicaset_alias)
        if cluster_replicaset is None:
            return None, "Replicaset '%s' isn't found in cluster" % replicaset_alias

        if leader_alias not in cluster_replicaset['instances']:
            return None, "Instance '%s' isn't found in replicaset '%s'" % (leader_alias, replicaset_alias)

        leader_instance = cluster_instances.get(leader_alias)
        if leader_instance is None:
            return None, "Instance '%s' isn't found in cluster" % leader_alias

        leader_instance_uuid = leader_instance.get('uuid')
        if not leader_instance_uuid:
            return None, "Instance '%s' has no UUID" % leader_alias

        replicaset_leaders.update({
            cluster_replicaset['uuid']: leader_instance_uuid,
        })

    return replicaset_leaders, None


def failover_promote(params):
    console_sock = params['console_sock']
    control_console = helpers.get_control_console(console_sock)

    err = check_leaders_promotion_is_possible(control_console)
    if err is not None:
        return helpers.ModuleRes(failed=True, msg=err)

    failover_promote_params = params.get('failover_promote_params')
    if failover_promote_params is None:
        failover_promote_params = {}

    critical_warnings = []

    # get replicaset leaders
    if params['promote_play_hosts']:
        module_hostvars = params['module_hostvars']
        cluster_disabled_instances = params['cluster_disabled_instances']
        play_hosts = params['play_hosts']

        replicaset_leaders, dead_replicasets = get_replicaset_leaders_by_play_hosts(
            play_hosts, module_hostvars, cluster_disabled_instances, control_console
        )
        if dead_replicasets:
            critical_warnings.append(
                'These replicasets have no alive instances across specified play hosts: %s' % ', '.join(
                    sorted(dead_replicasets)
                )
            )
    else:
        specified_replicaset_leaders = failover_promote_params.get('replicaset_leaders')

        replicaset_leaders, err = get_replicaset_leaders_by_aliases(
            specified_replicaset_leaders, control_console
        )

        if err is not None:
            return helpers.ModuleRes(failed=True, msg=err)

    if not replicaset_leaders:
        if critical_warnings:
            return helpers.ModuleRes(
                failed=True,
                msg="Failed to promote leaders: %s" % err,
                warnings=critical_warnings,
            )
        return helpers.ModuleRes(changed=False)

    force_inconsistency = failover_promote_params.get('force_inconsistency')

    # set two-phase commit opts
    helpers.set_twophase_options_from_params(control_console, params)

    active_leaders, _ = helpers.get_active_leaders(control_console)

    _, err = call_failover_promote(control_console, replicaset_leaders, force_inconsistency)
    if err is not None:
        return helpers.ModuleRes(
            failed=True,
            msg="Failed to promote leaders: %s" % err,
            warnings=critical_warnings,
        )

    new_active_leaders, _ = helpers.get_active_leaders(control_console)

    if critical_warnings:
        return helpers.ModuleRes(
            failed=True,
            msg="Promoted with critical warnings",
            warnings=critical_warnings
        )

    return helpers.ModuleRes(changed=active_leaders != new_active_leaders)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, failover_promote)
