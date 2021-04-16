#!/usr/bin/python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'failover_promote_params': {'required': False, 'type': 'dict'},
    'netbox_call_timeout': {'required': False, 'type': 'int'},
    'upload_config_timeout': {'required': False, 'type': 'int'},
    'apply_config_timeout': {'required': False, 'type': 'int'},
}


def failover_promote(params):
    console_sock = params['console_sock']

    failover_promote_params = params.get('failover_promote_params')
    if failover_promote_params is None:
        return helpers.ModuleRes(changed=False)

    specified_replicaset_leaders = failover_promote_params.get('replicaset_leaders')
    force_inconsistency = failover_promote_params.get('force_inconsistency')

    if not specified_replicaset_leaders:
        return helpers.ModuleRes(changed=False)

    control_console = helpers.get_control_console(console_sock)

    helpers.set_twophase_options_from_params(control_console, params)

    cluster_instances = helpers.get_cluster_instances(control_console)
    cluster_replicasets = helpers.get_cluster_replicasets(control_console)

    failover_mode, _ = control_console.eval_res_err('''
        local cartridge = require('cartridge')
        if cartridge.failover_get_params == nil then
            return nil
        end

        local failover_params = cartridge.failover_get_params()
        return failover_params.mode
    ''')

    if failover_mode != 'stateful':
        return helpers.ModuleRes(
            failed=True,
            msg="Leaders promotion is possible only when stateful failover is enabled"
        )

    active_leaders, _ = control_console.eval_res_err('''
        return require('cartridge.failover').get_active_leaders()
    ''')

    replicaset_leaders = {}
    for replicaset_alias, leader_alias in specified_replicaset_leaders.items():
        cluster_replicaset = cluster_replicasets.get(replicaset_alias)
        if cluster_replicaset is None:
            return helpers.ModuleRes(
                failed=True,
                msg="Replicaset '%s' isn't found in cluster" % replicaset_alias
            )

        if leader_alias not in cluster_replicaset['instances']:
            return helpers.ModuleRes(
                failed=True,
                msg="Instance '%s' isn't found in replicaset '%s'" % (leader_alias, replicaset_alias)
            )

        leader_instance = cluster_instances.get(leader_alias)
        if leader_instance is None:
            return helpers.ModuleRes(
                failed=True,
                msg="Instance '%s' isn't found in cluster" % leader_alias
            )

        leader_instance_uuid = leader_instance.get('uuid')
        if not leader_instance_uuid:
            return helpers.ModuleRes(
                failed=True,
                msg="Instance '%s' has no UUID" % leader_alias
            )

        replicaset_leaders.update({
            cluster_replicaset['uuid']: leader_instance_uuid,
        })

    _, err = control_console.eval_res_err('''
        return require('cartridge').failover_promote(...)
    ''', replicaset_leaders, force_inconsistency)

    if err is not None:
        return helpers.ModuleRes(
            failed=True,
            msg="Failed to promote leaders: %s" % err
        )

    new_active_leaders, _ = control_console.eval_res_err('''
        return require('cartridge.failover').get_active_leaders()
    ''')

    return helpers.ModuleRes(changed=active_leaders != new_active_leaders)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, failover_promote)
