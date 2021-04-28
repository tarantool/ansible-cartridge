#!/usr/bin/env python

import time

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'module_hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
    'console_sock': {'required': True, 'type': 'str'},
    'healthy_timeout': {'required': True, 'type': 'int'},
    'netbox_call_timeout': {'required': False, 'type': 'int'},
    'upload_config_timeout': {'required': False, 'type': 'int'},
    'apply_config_timeout': {'required': False, 'type': 'int'},
    'allow_missed_instances': {'required': True, 'type': 'bool'},
}

edit_topology_func_body = '''
%s
%s

local res, err = require('cartridge').admin_edit_topology(...)

if err ~= nil then
    return nil, err
end

local ret = {
    replicasets = setmetatable({}, {__serialize = 'map'}),
    servers = setmetatable({}, {__serialize = 'map'}),
}
for _, r in ipairs(res.replicasets or {}) do
    if r.alias ~= nil then
        ret.replicasets[r.alias] = format_replicaset(r)
    end
end

for _, s in ipairs(res.servers or {}) do
    if s.alias ~= nil then
        ret.servers[s.alias] = format_server(s)
    end
end
return ret
''' % (helpers.FORMAT_REPLICASET_FUNC, helpers.FORMAT_SERVER_FUNC)


def get_configured_replicasets(module_hostvars, play_hosts):
    replicasets = {}

    for instance_name in play_hosts:
        instance_vars = module_hostvars[instance_name]

        if helpers.is_expelled(instance_vars) or helpers.is_stateboard(instance_vars):
            continue

        if instance_vars.get('replicaset_alias') is None:
            continue

        replicaset_alias = instance_vars['replicaset_alias']
        if replicaset_alias not in replicasets:
            replicasets.update({
                replicaset_alias: {
                    'instances': [],
                    'roles': instance_vars.get('roles', None),
                    'failover_priority': instance_vars.get('failover_priority', None),
                    'all_rw': instance_vars.get('all_rw', None),
                    'weight': instance_vars.get('weight', None),
                    'vshard_group': instance_vars.get('vshard_group', None),
                    'alias': replicaset_alias,
                }
            })
        replicasets[replicaset_alias]['instances'].append(instance_name)

    return replicasets


def get_instances_to_configure(module_hostvars, play_hosts):
    instances = {}

    for instance_name in play_hosts:
        instance_vars = module_hostvars[instance_name]

        if helpers.is_stateboard(instance_vars):
            continue

        instance = {}

        if helpers.is_expelled(instance_vars):
            instance['expelled'] = True
        else:
            if 'zone' in instance_vars:
                instance['zone'] = instance_vars['zone']
            if 'config' in instance_vars:
                if 'advertise_uri' in instance_vars['config']:
                    instance['uri'] = instance_vars['config']['advertise_uri']

        if instance:
            instances[instance_name] = instance

    return instances


def add_replicaset_param_if_required(replicaset_params, replicaset, cluster_replicaset, param_name):
    if replicaset.get(param_name) is None:
        return

    if cluster_replicaset is not None:
        if param_name == 'roles':
            if set(replicaset.get('roles', [])) == set(cluster_replicaset.get('roles', [])):
                return

        if replicaset.get(param_name) == cluster_replicaset.get(param_name):
            return

    replicaset_params[param_name] = replicaset.get(param_name)


def get_join_servers(replicaset, cluster_replicaset, cluster_instances, allow_missed_instances):
    current_instances = []
    if cluster_replicaset is not None:
        current_instances = cluster_replicaset.get('instances')

    remaining_instances = set(replicaset['instances']) - set(current_instances)
    if not remaining_instances:
        return None, None

    instances_to_join = list(filter(lambda s: s in cluster_instances, remaining_instances))

    if len(instances_to_join) < len(remaining_instances):
        instances_not_in_cluster_str = ', '.join(sorted(
            remaining_instances.difference(set(instances_to_join))
        ))

        msg = "Some of replicaset instances aren't found in cluster: %s" % instances_not_in_cluster_str

        if allow_missed_instances:
            helpers.warn(msg)
        else:
            return None, msg

    # generally, we always apply failover priority AFTER
    # all other changes
    # the only one optimization is to join new replicaset
    # with failover priority
    # and call second `edit_topology` only for replicasets that have
    # failover priority different from the specified

    if instances_to_join:
        if cluster_replicaset is None:
            # we create new replicaset - let's join instances in failover priority
            # to avoid second edit_toplogy call
            failover_priority = replicaset.get('failover_priority')
            if failover_priority:
                started_failover_priority_instances = set(filter(
                    lambda s: s in cluster_instances, failover_priority
                ))

                if len(started_failover_priority_instances) < len(failover_priority):
                    instances_not_in_cluster_str = ', '.join(sorted(
                        set(failover_priority).difference(started_failover_priority_instances)
                    ))

                    msg = "Some of instances specified in failover_priority aren't found in cluster: %s" % (
                        instances_not_in_cluster_str
                    )
                    if allow_missed_instances:
                        helpers.warn(msg)
                    else:
                        return None, msg

                instances_to_join = list(sorted(
                    instances_to_join,
                    key=lambda s: failover_priority.index(s) if s in failover_priority else len(instances_to_join)
                ))

    join_servers = [
        {'uri': cluster_instances[s]['uri']}
        for s in instances_to_join
    ]

    return join_servers, None


def get_replicaset_params(replicaset, cluster_replicaset, cluster_instances, allow_missed_instances):
    """
    input EditReplicasetInput {
        uuid: String
        weight: Float
        vshard_group: String
        join_servers: [JoinServerInput]
        roles: [String!]
        alias: String!
        all_rw: Boolean
        failover_priority: [String!]
    }
    """

    replicaset_params = {}

    if cluster_replicaset is not None:
        replicaset_params['uuid'] = cluster_replicaset['uuid']
    else:
        replicaset_params['alias'] = replicaset['alias']

    for param_name in ['weight', 'vshard_group', 'all_rw', 'roles']:
        add_replicaset_param_if_required(
            replicaset_params, replicaset, cluster_replicaset, param_name
        )

    join_servers, err = get_join_servers(
        replicaset, cluster_replicaset, cluster_instances, allow_missed_instances
    )
    if err is not None:
        return None, err

    if join_servers:
        replicaset_params['join_servers'] = join_servers

    if 'uuid' in replicaset_params and len(replicaset_params) == 1:
        # replicaset is already exists
        # and all parameters are the same as configured
        return None, None

    return replicaset_params, None


def get_replicasets_params(replicasets, cluster_replicasets, cluster_instances, allow_missed_instances):
    replicasets_params = []

    for _, replicaset in replicasets.items():
        cluster_replicaset = cluster_replicasets.get(replicaset['alias'])

        replicaset_params, err = get_replicaset_params(
            replicaset, cluster_replicaset, cluster_instances, allow_missed_instances
        )

        if err is not None:
            return None, "Failed to get edit topology params for replicaset %s: %s" % (
                replicaset['alias'], err
            )

        if replicaset_params is not None:
            replicasets_params.append(replicaset_params)

    return replicasets_params, None


def get_replicasets_params_for_changing_failover_priority(replicasets, cluster_replicasets,
                                                          cluster_instances, allow_missed_instances):
    replicasets_params = []

    for alias, cluster_replicaset in cluster_replicasets.items():
        if alias not in replicasets:
            continue

        failover_priority = replicasets[alias].get('failover_priority')
        if failover_priority is None:
            continue

        if cluster_replicaset['instances'][:len(failover_priority)] != failover_priority:
            failover_priority_uuids = []
            for instance_name in failover_priority:
                if instance_name not in cluster_instances or not cluster_instances[instance_name].get('uuid'):
                    msg = "Instance %s from %s failover_priority isn't joined to cluster" % (
                        instance_name, alias
                    )

                    if allow_missed_instances:
                        helpers.warn(msg)
                        continue
                    else:
                        return None, msg
                failover_priority_uuids.append(cluster_instances[instance_name]['uuid'])

            replicasets_params.append({
                'uuid': cluster_replicaset['uuid'],
                'failover_priority': failover_priority_uuids,
            })

    return replicasets_params, None


def add_server_param_if_required(server_params, instance_params, cluster_instance, param_name):
    if instance_params.get(param_name) is None:
        return

    if cluster_instance is not None:
        if instance_params.get(param_name) == cluster_instance.get(param_name):
            return

    server_params[param_name] = instance_params.get(param_name)


def get_server_params(instance_name, instance_params, cluster_instances, allow_missed_instances):
    if instance_name not in cluster_instances:
        if instance_params.get('expelled') is True:
            return None, None

        msg = "Instance %s isn't found in cluster" % instance_name
        if allow_missed_instances:
            helpers.warn(msg)
            return None, None
        else:
            return None, msg

    cluster_instance = cluster_instances[instance_name]

    if not cluster_instance.get('uuid'):  # uuid is '' for unjoined instances
        return None, None

    server_params = {
        'uuid': cluster_instance.get('uuid'),
    }

    if instance_params.get('expelled') is True:
        server_params['expelled'] = True
    else:
        for param_name in ['zone', 'uri']:
            add_server_param_if_required(server_params, instance_params, cluster_instance, param_name)

    if len(server_params) == 1:
        # there are only `uuid`, all instance parameters are the same as configured
        return None, None

    return server_params, None


def get_servers_params(instances, cluster_instances, allow_missed_instances):
    servers_params = []
    for instance_name, instance_params in instances.items():
        server_params, err = get_server_params(
            instance_name, instance_params, cluster_instances, allow_missed_instances
        )
        if err is not None:
            return None, "Failed to get edit topology params for instance %s: %s" % (instance_name, err)

        if server_params is not None:
            servers_params.append(server_params)

    return servers_params, None


def get_topology_params(replicasets, cluster_replicasets, instances, cluster_instances, allow_missed_instances):
    topology_params = {}

    replicasets_params, err = get_replicasets_params(
        replicasets, cluster_replicasets, cluster_instances, allow_missed_instances
    )
    if err is not None:
        return None, err

    if replicasets_params:
        topology_params['replicasets'] = replicasets_params

    servers_params, err = get_servers_params(instances, cluster_instances, allow_missed_instances)
    if err is not None:
        return None, err

    if servers_params:
        topology_params['servers'] = servers_params

    return topology_params, None


def get_replicasets_failover_priority_and_instances_params(
    replicasets, cluster_replicasets, instances, cluster_instances, allow_missed_instances
):
    topology_params = {}

    replicasets_params, err = get_replicasets_params_for_changing_failover_priority(
        replicasets, cluster_replicasets, cluster_instances, allow_missed_instances
    )
    if err is not None:
        return None, err

    if replicasets_params:
        topology_params['replicasets'] = replicasets_params

    # manage instances that were joined on previous call
    servers_params, err = get_servers_params(instances, cluster_instances, allow_missed_instances)
    if err is not None:
        return None, err

    if servers_params:
        topology_params['servers'] = servers_params

    return topology_params, None


def wait_for_cluster_is_healthy(control_console, timeout):
    delay = 0.5
    time_start = time.time()

    while True:
        is_healthy, _ = control_console.eval_res_err('''
            return require('cartridge').is_healthy()
        ''')

        if is_healthy:
            return True

        if time.time() > time_start + timeout:
            return False

        time.sleep(delay)


def update_cluster_instances_and_replicasets(
    edit_topology_res, instances, cluster_instances, cluster_replicasets
):
    # instances
    for alias, res_instance in edit_topology_res['servers'].items():
        cluster_instances[alias] = res_instance

    # remove expelled instances
    for alias, instance in instances.items():
        if instance.get('expelled') and alias in cluster_instances:
            del cluster_instances[alias]

    # replicasets
    for alias, res_replicaset in edit_topology_res['replicasets'].items():
        cluster_replicasets[alias] = res_replicaset


def edit_topology(params):
    console_sock = params['console_sock']
    module_hostvars = params['module_hostvars']
    play_hosts = params['play_hosts']
    healthy_timeout = params['healthy_timeout']
    allow_missed_instances = params['allow_missed_instances']

    replicasets = get_configured_replicasets(module_hostvars, play_hosts)
    instances = get_instances_to_configure(module_hostvars, play_hosts)

    if not replicasets and not instances:
        return helpers.ModuleRes(changed=False)

    control_console = helpers.get_control_console(console_sock)

    helpers.set_twophase_options_from_params(control_console, params)

    cluster_instances = helpers.get_cluster_instances(control_console)
    cluster_replicasets = helpers.get_cluster_replicasets(control_console)

    # Configure replicasets and instances:
    # * Create new replicasets.
    # * Edit existent replicasets and join new instances to them.
    #   In this case failover_priority isn't changed since
    #   new instances hasn't UUIDs before join.
    # * Expel instances.
    # * Configure instances that are already joined.
    #   New instances aren't configured here since they don't have
    #   UUIDs before join.
    topology_params, err = get_topology_params(
        replicasets, cluster_replicasets, instances, cluster_instances, allow_missed_instances
    )
    if err is not None:
        return helpers.ModuleRes(
            failed=True,
            msg="Failed to collect edit topology params: %s" % err
        )

    topology_changed = False

    if topology_params:
        res, err = control_console.eval_res_err(edit_topology_func_body, topology_params)
        if err is not None:
            return helpers.ModuleRes(failed=True, msg="Failed to edit topology: %s" % err)

        topology_changed = True

        # Without this `Peer closed` error is returned on second `edit_topology`
        # call in some cases (e.g. when new instance is joined at first call
        # and then it's configured on second)
        # See https://github.com/tarantool/cartridge/issues/1320
        # The simplest w/a is to add a little delay between this calls,
        # and we just perform `is_healthy` call here.
        # If everything is Ok - this call doesn't take a long time, but
        # guarantees that next `edit_topology` call wouldn't fail.
        # If cluster isn't healthy then it's good to show error.
        if not wait_for_cluster_is_healthy(control_console, healthy_timeout):
            return helpers.ModuleRes(
                failed=True, msg="Cluster isn't healthy after editing topology"
            )

        # Now we need to get updated instances and replicasets
        # configuration to check if we need one more call.
        # `edit_topology` returns summary of updated instances
        # so let's use it to update cluster_instances and cluster_replicasets.
        update_cluster_instances_and_replicasets(
            res, instances, cluster_instances, cluster_replicasets
        )

    # Configure failover_priority and instances that were joined on previous call:
    # * Edit failover_priority of replicasets if it's needed.
    # * Configure instances that weren't configured on first `edit_topology` call.
    topology_params, err = get_replicasets_failover_priority_and_instances_params(
        replicasets, cluster_replicasets, instances, cluster_instances, allow_missed_instances
    )
    if err is not None:
        return helpers.ModuleRes(
            failed=True,
            msg="Failed to collect edit topology params for changing failover_priority "
                "and configuring new instances: %s" % err
        )

    if topology_params:
        res, err = control_console.eval_res_err(edit_topology_func_body, topology_params)
        if err is not None:
            return helpers.ModuleRes(
                failed=True,
                msg="Failed to edit failover priority and configure instances: %s" % err
            )

        topology_changed = True

        if not wait_for_cluster_is_healthy(control_console, healthy_timeout):
            return helpers.ModuleRes(
                failed=True, msg="Cluster isn't healthy after editing failover priority and configuring instances"
            )

    return helpers.ModuleRes(changed=topology_changed)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, edit_topology)
