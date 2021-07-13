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


###############################################
# Collect information about inventory cluster #
###############################################


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


def get_replicasets_to_configure(module_hostvars, play_hosts):
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


def set_enabled_roles(replicasets, control_console):
    roles_by_aliases = {alias: r['roles'] for alias, r in replicasets.items()}

    if not roles_by_aliases:
        return

    enabled_roles_by_aliases, _ = control_console.eval_res_err('''
        local cartridge_roles = require('cartridge.roles')

        local roles_by_aliases = ...
        local enabled_roles_by_aliases = {}

        for alias, roles in pairs(roles_by_aliases) do
            enabled_roles_by_aliases[alias] = cartridge_roles.get_enabled_roles(roles or {})
        end

        return enabled_roles_by_aliases
    ''', roles_by_aliases)

    for alias, enabled_roles in enabled_roles_by_aliases.items():
        replicasets[alias].update({
            'enabled_roles': enabled_roles,
        })


#############################################################
# Collect difference between real and inventory replicasets #
#############################################################


def add_replicaset_param_if_required(replicaset_params, replicaset, cluster_replicaset, param_name):
    if replicaset.get(param_name) is None:
        return

    if cluster_replicaset is not None:
        if replicaset.get(param_name) == cluster_replicaset.get(param_name):
            return

    replicaset_params[param_name] = replicaset.get(param_name)


def add_replicaset_roles_param_if_required(replicaset_params, replicaset, cluster_replicaset):
    if replicaset.get('roles') is None:
        return

    if cluster_replicaset is not None:
        if set(replicaset['enabled_roles']) == set(cluster_replicaset['enabled_roles']):
            return

    replicaset_params['roles'] = replicaset['roles']


def check_filtered_instances(instances, filtered_instances, fmt, allow_missed_instances):
    if len(instances) == len(filtered_instances):
        return None

    missed_instances = ', '.join(sorted(
        set(instances).difference(filtered_instances)
    ))

    msg = fmt % missed_instances

    if allow_missed_instances:
        helpers.warn(msg)
        return None

    return msg


def sort_instances_to_join_by_failover_priority(
    instances_to_join, replicaset, cluster_instances, allow_missed_instances
):
    failover_priority = replicaset.get('failover_priority')
    if not failover_priority:
        return instances_to_join, None

    started_failover_priority_instances = set(filter(
        lambda s: s in cluster_instances, failover_priority
    ))

    err = check_filtered_instances(
        failover_priority,
        started_failover_priority_instances,
        "Some of instances specified in failover_priority aren't found in cluster: %s",
        allow_missed_instances
    )

    if err is not None:
        return None, err

    instances_to_join = list(sorted(
        instances_to_join,
        key=lambda s: failover_priority.index(s) if s in failover_priority else len(instances_to_join)
    ))

    return instances_to_join, None


def get_join_servers(replicaset, cluster_replicaset, cluster_instances, allow_missed_instances):
    current_instances = []
    if cluster_replicaset is not None:
        current_instances = cluster_replicaset.get('instances')

    remaining_instances = set(replicaset['instances']) - set(current_instances)
    if not remaining_instances:
        return None, None

    instances_to_join = list(filter(lambda s: s in cluster_instances, remaining_instances))

    err = check_filtered_instances(
        remaining_instances,
        instances_to_join,
        "Some of replicaset instances aren't found in cluster: %s",
        allow_missed_instances
    )

    if err is not None:
        return None, err

    # When the new replicaset is created, instances can be joined in failover
    # priority order.
    # When the existing replicaset is edited, failover priority is configured
    # later when all replicaset instances UUIDs are set (when new instances
    # are joined, UUID isn't specified).

    if instances_to_join:
        if cluster_replicaset is None:
            # we create new replicaset - let's join instances in failover priority
            # to avoid second edit_toplogy call
            instances_to_join, err = sort_instances_to_join_by_failover_priority(
                instances_to_join, replicaset, cluster_instances, allow_missed_instances
            )
            if err is not None:
                return None, err

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

    for param_name in ['weight', 'vshard_group', 'all_rw']:
        add_replicaset_param_if_required(
            replicaset_params, replicaset, cluster_replicaset, param_name
        )

    add_replicaset_roles_param_if_required(
        replicaset_params, replicaset, cluster_replicaset
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


def get_replicasets_params(
    replicasets, cluster_replicasets,
    cluster_instances,
    allow_missed_instances,
):
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


def get_replicasets_params_for_changing_failover_priority(
    replicasets, cluster_replicasets,
    cluster_instances,
    allow_missed_instances,
):
    replicasets_params = []

    for alias, cluster_replicaset in cluster_replicasets.items():
        if alias not in replicasets:
            continue

        failover_priority = replicasets[alias].get('failover_priority')
        if failover_priority is None:
            continue

        if cluster_replicaset['instances'][:len(failover_priority)] == failover_priority:
            continue

        filtered_failover_priority = list(filter(
            lambda s: s in cluster_instances and cluster_instances[s].get('uuid'),
            failover_priority
        ))

        err = check_filtered_instances(
            failover_priority,
            filtered_failover_priority,
            "Instances %s from %s failover_priority aren't joined to cluster" % ("%s", alias),
            allow_missed_instances,
        )

        if err is not None:
            return None, err

        failover_priority_uuids = [
            cluster_instances[s]['uuid'] for s in filtered_failover_priority
        ]

        replicasets_params.append({
            'uuid': cluster_replicaset['uuid'],
            'failover_priority': failover_priority_uuids,
        })

    return replicasets_params, None


#########################################################
# Collect difference between real and inventory servers #
#########################################################


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


#########################
# Edit topology helpers #
#########################


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


#################
# Main function #
################


def get_topology_params(
    get_replicasets_params_func,
    replicasets, cluster_replicasets,
    instances, cluster_instances,
    allow_missed_instances,
):
    topology_params = {}

    replicasets_params, err = get_replicasets_params_func(
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


def single_edit_topology_call(
    control_console,
    get_replicasets_params_func,
    instances, cluster_instances,
    replicasets, cluster_replicasets,
    allow_missed_instances,
    healthy_timeout,
):
    topology_params, err = get_topology_params(
        get_replicasets_params_func,
        replicasets, cluster_replicasets,
        instances, cluster_instances,
        allow_missed_instances,
    )
    if err is not None:
        return None, "Failed to collect edit topology params: %s" % err

    if not topology_params:
        return False, None

    res, err = control_console.eval_res_err(edit_topology_func_body, topology_params)
    if err is not None:
        return None, 'Failed to edit topology: %s' % err

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
        return None, "Cluster isn't healthy after editing topology"

    # Now we need to get updated instances and replicasets
    # configuration to check if we need one more call.
    # `edit_topology` returns summary of updated instances
    # so let's use it to update cluster_instances and cluster_replicasets.
    update_cluster_instances_and_replicasets(
        res, instances, cluster_instances, cluster_replicasets
    )

    return True, None


def edit_topology(params):
    console_sock = params['console_sock']
    module_hostvars = params['module_hostvars']
    play_hosts = params['play_hosts']
    healthy_timeout = params['healthy_timeout']
    allow_missed_instances = params['allow_missed_instances']

    # Collect information about instances and replicasets from inventory

    instances = get_instances_to_configure(module_hostvars, play_hosts)
    replicasets = get_replicasets_to_configure(module_hostvars, play_hosts)

    if not replicasets and not instances:
        return helpers.ModuleRes(changed=False)

    # Collect information about instances and replicasets from cluster

    control_console = helpers.get_control_console(console_sock)
    helpers.set_twophase_options_from_params(control_console, params)

    set_enabled_roles(replicasets, control_console)

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

    first_call_changed, err = single_edit_topology_call(
        control_console,
        get_replicasets_params,
        instances, cluster_instances,
        replicasets, cluster_replicasets,
        allow_missed_instances,
        healthy_timeout,
    )
    if err is not None:
        return helpers.ModuleRes(failed=True, msg=err)

    # Configure failover_priority and instances that were joined on previous call:
    # * Edit failover_priority of replicasets if it's needed.
    # * Configure instances that weren't configured on first `edit_topology` call.

    second_call_changed, err = single_edit_topology_call(
        control_console,
        get_replicasets_params_for_changing_failover_priority,
        instances, cluster_instances,
        replicasets, cluster_replicasets,
        allow_missed_instances,
        healthy_timeout,
    )
    if err is not None:
        return helpers.ModuleRes(failed=True, msg=err)

    return helpers.ModuleRes(changed=first_call_changed or second_call_changed)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, edit_topology)
