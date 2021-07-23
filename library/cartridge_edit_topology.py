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
    'check_mode': {'required': False, 'type': 'bool', 'default': False},
    'ignore_errors_of_checks': {'required': False, 'type': 'dict', 'default': {}},
}

ADVERTISE_URIS_CHANGE_CHECK_NAME = 'advertise_uris_change'
EXTRA_CLUSTER_INSTANCES_CHECK_NAME = 'extra_cluster_instances'
EXTRA_CLUSTER_REPLICASETS_CHECK_NAME = 'extra_cluster_replicasets'
RENAMED_REPLICASETS_CHECK_NAME = 'renamed_replicasets'

EDIT_TOPOLOGY_FUNC_BODY = '''
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


##########################################
# Collect information about new topology #
##########################################


def get_all_new_instances(module_hostvars):
    instances = {}

    for instance_name, instance_vars in module_hostvars.items():
        if helpers.is_stateboard(instance_vars):
            continue

        instance = {}

        if helpers.is_expelled(instance_vars):
            instance['expelled'] = True
        else:
            if instance_vars.get('zone') is not None:
                instance['zone'] = instance_vars['zone']
            if instance_vars.get('config') is not None:
                if 'advertise_uri' in instance_vars['config']:
                    instance['uri'] = instance_vars['config']['advertise_uri']

        if instance:
            instances[instance_name] = instance

    return instances


def get_new_instances(module_hostvars, play_hosts):
    module_hostvars = {
        instance_name: instance_vars
        for instance_name, instance_vars in module_hostvars.items()
        if instance_name in play_hosts
    }
    return get_all_new_instances(module_hostvars)


def get_all_new_replicasets(module_hostvars):
    replicasets = {}

    for instance_name, instance_vars in module_hostvars.items():
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


def get_new_replicasets(module_hostvars, play_hosts):
    module_hostvars = {
        instance_name: instance_vars
        for instance_name, instance_vars in module_hostvars.items()
        if instance_name in play_hosts
    }
    return get_all_new_replicasets(module_hostvars)


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


######################################################
# Collect difference between old and new replicasets #
######################################################


def add_replicaset_param_if_required(replicaset_params, new_replicaset, old_replicaset, param_name):
    if new_replicaset.get(param_name) is None:
        return

    if old_replicaset is not None:
        if new_replicaset.get(param_name) == old_replicaset.get(param_name):
            return

    replicaset_params[param_name] = new_replicaset.get(param_name)


def add_replicaset_roles_param_if_required(replicaset_params, new_replicaset, old_replicaset):
    if new_replicaset.get('roles') is None:
        return

    if old_replicaset is not None:
        if set(new_replicaset['enabled_roles']) == set(old_replicaset['enabled_roles']):
            return

    replicaset_params['roles'] = new_replicaset['roles']


def check_for_missed_instances(instances, filtered_instances, fmt, allow_missed_instances):
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
    instances_to_join, new_replicaset, old_instances, allow_missed_instances
):
    new_failover_priority = new_replicaset.get('failover_priority')
    if not new_failover_priority:
        return instances_to_join, None

    started_failover_priority_instances = set(filter(
        lambda s: s in old_instances, new_failover_priority
    ))

    err = check_for_missed_instances(
        new_failover_priority,
        started_failover_priority_instances,
        "Some of instances specified in failover_priority aren't found in cluster: %s",
        allow_missed_instances
    )

    if err is not None:
        return None, err

    instances_to_join = list(sorted(
        instances_to_join,
        key=lambda s: new_failover_priority.index(s) if s in new_failover_priority else len(instances_to_join)
    ))

    return instances_to_join, None


def get_join_servers(new_replicaset, old_replicaset, old_instances, allow_missed_instances):
    current_instances = []
    if old_replicaset is not None:
        current_instances = old_replicaset.get('instances')

    remaining_instances = set(new_replicaset['instances']) - set(current_instances)
    if not remaining_instances:
        return None, None

    instances_to_join = list(filter(lambda s: s in old_instances, remaining_instances))

    err = check_for_missed_instances(
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
        if old_replicaset is None:
            # we create new replicaset - let's join instances in failover priority
            # to avoid second edit_topology call
            instances_to_join, err = sort_instances_to_join_by_failover_priority(
                instances_to_join, new_replicaset, old_instances, allow_missed_instances
            )
            if err is not None:
                return None, err

    join_servers = [
        {'uri': old_instances[s]['uri']}
        for s in instances_to_join
    ]

    return join_servers, None


def get_replicaset_params(new_replicaset, old_replicaset, old_instances, allow_missed_instances):
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

    if old_replicaset is not None:
        replicaset_params['uuid'] = old_replicaset['uuid']
    else:
        replicaset_params['alias'] = new_replicaset['alias']

    for param_name in ['weight', 'vshard_group', 'all_rw']:
        add_replicaset_param_if_required(
            replicaset_params, new_replicaset, old_replicaset, param_name
        )

    add_replicaset_roles_param_if_required(
        replicaset_params, new_replicaset, old_replicaset
    )

    join_servers, err = get_join_servers(
        new_replicaset, old_replicaset, old_instances, allow_missed_instances
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
    new_replicasets, old_replicasets,
    old_instances,
    allow_missed_instances,
):
    replicasets_params = []

    for _, new_replicaset in new_replicasets.items():
        old_replicaset = old_replicasets.get(new_replicaset['alias'])

        replicaset_params, err = get_replicaset_params(
            new_replicaset, old_replicaset, old_instances, allow_missed_instances
        )

        if err is not None:
            return None, "Failed to get edit topology params for replicaset %s: %s" % (
                new_replicaset['alias'], err
            )

        if replicaset_params is not None:
            replicasets_params.append(replicaset_params)

    return replicasets_params, None


def get_replicasets_params_for_changing_failover_priority(
    new_replicasets, old_replicasets,
    old_instances,
    allow_missed_instances,
):
    replicasets_params = []

    for alias, old_replicaset in old_replicasets.items():
        if alias not in new_replicasets:
            continue

        new_failover_priority = new_replicasets[alias].get('failover_priority')
        if new_failover_priority is None:
            continue

        if old_replicaset['instances'][:len(new_failover_priority)] == new_failover_priority:
            continue

        filtered_new_failover_priority = list(filter(
            lambda s: s in old_instances and old_instances[s].get('uuid'),
            new_failover_priority
        ))

        err = check_for_missed_instances(
            new_failover_priority,
            filtered_new_failover_priority,
            "Instances %s from %s failover_priority aren't joined to cluster" % ("%s", alias),
            allow_missed_instances,
        )

        if err is not None:
            return None, err

        new_failover_priority_uuids = [
            old_instances[s]['uuid'] for s in filtered_new_failover_priority
        ]

        replicasets_params.append({
            'uuid': old_replicaset['uuid'],
            'failover_priority': new_failover_priority_uuids,
        })

    return replicasets_params, None


####################################################
# Collect difference between old and new instances #
####################################################


def add_server_param_if_required(server_params, new_instance, old_instance, param_name):
    if new_instance.get(param_name) is None:
        return

    if old_instance is not None:
        if new_instance.get(param_name) == old_instance.get(param_name):
            return

    server_params[param_name] = new_instance.get(param_name)


def get_server_params(instance_name, new_instance, old_instances, allow_missed_instances):
    if instance_name not in old_instances:
        if new_instance.get('expelled') is True:
            return None, None

        msg = "Instance %s isn't found in cluster" % instance_name
        if allow_missed_instances:
            helpers.warn(msg)
            return None, None
        else:
            return None, msg

    old_instance = old_instances[instance_name]

    if not old_instance.get('uuid'):  # uuid is '' for unjoined instances
        return None, None

    server_params = {
        'uuid': old_instance.get('uuid'),
    }

    if new_instance.get('expelled') is True:
        server_params['expelled'] = True
    else:
        for param_name in ['zone', 'uri']:
            add_server_param_if_required(server_params, new_instance, old_instance, param_name)

    if len(server_params) == 1:
        # there are only `uuid`, all instance parameters are the same as configured
        return None, None

    return server_params, None


def get_servers_params(
    new_instances, old_instances,
    allow_missed_instances,
):
    servers_params = []
    for instance_name, new_instance in new_instances.items():
        server_params, err = get_server_params(
            instance_name, new_instance, old_instances, allow_missed_instances
        )
        if err is not None:
            return None, "Failed to get edit topology params for instance %s: %s" % (instance_name, err)

        if server_params is not None:
            servers_params.append(server_params)

    return servers_params, None


##############
# Check mode #
##############

def check_new_instances_for_dangerous_changes(
    all_new_instances, new_instances, old_instances,
    ignore_errors_of_checks,
):
    errors = []
    extra_cluster_instances = []
    changed_advertise_uris = []

    for instance_name in old_instances.keys():
        if instance_name not in all_new_instances:
            extra_cluster_instances.append(instance_name)
        elif instance_name in new_instances:
            new_uri = new_instances[instance_name].get('uri')
            old_uri = old_instances[instance_name].get('uri')
            if new_uri != old_uri:
                changed_advertise_uris.append('%s (%s -> %s)' % (instance_name, old_uri, new_uri))

    if changed_advertise_uris:
        msg = 'advertise uris of some instances were changed in inventory: %s'
        msg %= ', '.join(changed_advertise_uris)
        if ignore_errors_of_checks.get(ADVERTISE_URIS_CHANGE_CHECK_NAME):
            helpers.warn(msg)
        else:
            errors.append(msg)

    if extra_cluster_instances:
        msg = 'some instances from cluster are missing in inventory, you should add them: %s'
        msg %= ', '.join(extra_cluster_instances)
        if ignore_errors_of_checks.get(EXTRA_CLUSTER_INSTANCES_CHECK_NAME):
            helpers.warn(msg)
        else:
            errors.append(msg)

    return errors


def check_new_replicasets_for_dangerous_changes(
    all_new_replicasets, new_replicasets, old_replicasets,
    ignore_errors_of_checks,
):
    errors = []
    extra_cluster_replicasets = []
    renamed_replicasets = []

    for old_replicaset_name, old_replicaset in old_replicasets.items():
        if old_replicaset_name in all_new_replicasets:
            continue

        renamed = False

        for new_replicaset_name, new_replicaset in all_new_replicasets.items():
            if set(new_replicaset.get('instances', [])) != set(old_replicaset.get('instances', [])):
                continue

            renamed = True
            # Ignore renamed replicaset if it isn't in play hosts
            if new_replicaset_name in new_replicasets:
                renamed_replicasets.append('%s -> %s' % (new_replicaset_name, old_replicaset_name))

        if not renamed:
            extra_cluster_replicasets.append(old_replicaset_name)

    if renamed_replicasets:
        msg = 'looks like that some replicasets has been renamed in UI, you should rename them in inventory: %s'
        msg %= ', '.join(renamed_replicasets)
        if ignore_errors_of_checks.get(RENAMED_REPLICASETS_CHECK_NAME):
            helpers.warn(msg)
        else:
            errors.append(msg)

    if extra_cluster_replicasets:
        msg = 'some replicasets from cluster are missing in inventory, you should add them: %s'
        msg %= ', '.join(extra_cluster_replicasets)
        if ignore_errors_of_checks.get(EXTRA_CLUSTER_REPLICASETS_CHECK_NAME):
            helpers.warn(msg)
        else:
            errors.append(msg)

    return errors


def check_new_cluster_for_dangerous_changes(
    all_new_instances, new_instances, old_instances,
    all_new_replicasets, new_replicasets, old_replicasets,
    ignore_errors_of_checks,
):
    errors = []
    errors += check_new_instances_for_dangerous_changes(
        all_new_instances,
        new_instances,
        old_instances,
        ignore_errors_of_checks,
    )
    errors += check_new_replicasets_for_dangerous_changes(
        all_new_replicasets,
        new_replicasets,
        old_replicasets,
        ignore_errors_of_checks,
    )
    if errors:
        error_fmt = (
            "Found dangerous changes in topology: %s. "
            "You can make changes in inventory or ignore this errors with the appropriate flags "
            "(see 'edit_topology' step documentation)."
        )
        return error_fmt % '; '.join(errors)
    return None


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


def update_old_instances_and_replicasets(
    edit_topology_res, new_instances, old_instances, old_replicasets
):
    # instances
    for alias, res_instance in edit_topology_res['servers'].items():
        old_instances[alias] = res_instance

    # remove expelled instances
    for alias, instance in new_instances.items():
        if instance.get('expelled') and alias in old_instances:
            del old_instances[alias]

    # replicasets
    for alias, res_replicaset in edit_topology_res['replicasets'].items():
        old_replicasets[alias] = res_replicaset


#################
# Main function #
################


def get_topology_params(
    get_replicasets_params_func,
    new_instances, old_instances,
    new_replicasets, old_replicasets,
    allow_missed_instances,
):
    topology_params = {}

    replicasets_params, err = get_replicasets_params_func(
        new_replicasets, old_replicasets,
        old_instances,
        allow_missed_instances,
    )
    if err is not None:
        return None, err

    if replicasets_params:
        topology_params['replicasets'] = replicasets_params

    servers_params, err = get_servers_params(
        new_instances, old_instances,
        allow_missed_instances,
    )
    if err is not None:
        return None, err

    if servers_params:
        topology_params['servers'] = servers_params

    return topology_params, None


def single_edit_topology_call(
    control_console,
    get_replicasets_params_func,
    new_instances, old_instances,
    new_replicasets, old_replicasets,
    allow_missed_instances,
    healthy_timeout,
):
    topology_params, err = get_topology_params(
        get_replicasets_params_func,
        new_instances, old_instances,
        new_replicasets, old_replicasets,
        allow_missed_instances,
    )
    if err is not None:
        return None, "Failed to collect edit topology params: %s" % err

    if not topology_params:
        return False, None

    res, err = control_console.eval_res_err(EDIT_TOPOLOGY_FUNC_BODY, topology_params)
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
    # so let's use it to update old_instances and old_replicasets.
    update_old_instances_and_replicasets(
        res, new_instances, old_instances, old_replicasets
    )

    return True, None


def edit_topology(params):
    console_sock = params['console_sock']
    module_hostvars = params['module_hostvars']
    play_hosts = params['play_hosts']
    healthy_timeout = params['healthy_timeout']
    allow_missed_instances = params['allow_missed_instances']
    check_mode = params.get('check_mode', False)
    ignore_errors_of_checks = params.get('ignore_errors_of_checks', {})

    # Collect information about instances and replicasets from inventory

    new_instances = get_new_instances(module_hostvars, play_hosts)
    new_replicasets = get_new_replicasets(module_hostvars, play_hosts)

    if not new_replicasets and not new_instances:
        return helpers.ModuleRes(changed=False)

    all_new_instances = get_all_new_instances(module_hostvars)
    all_new_replicasets = get_all_new_replicasets(module_hostvars)

    # Collect information about instances and replicasets from cluster

    control_console = helpers.get_control_console(console_sock)
    helpers.set_twophase_options_from_params(control_console, params)

    set_enabled_roles(new_replicasets, control_console)

    old_instances = helpers.get_cluster_instances(control_console)
    old_replicasets = helpers.get_cluster_replicasets(control_console)

    # Check for dangerous changes

    if check_mode:
        err = check_new_cluster_for_dangerous_changes(
            all_new_instances, new_instances, old_instances,
            all_new_replicasets, new_replicasets, old_replicasets,
            ignore_errors_of_checks,
        )
        if err is not None:
            return helpers.ModuleRes(failed=True, msg=err)
        return helpers.ModuleRes(changed=False)

    # Configure replicasets and instances:
    # * Create new replicasets.
    # * Edit existent replicasets and join new instances to them.
    #   In this case failover_priority isn't changed since
    #   new instances hasn't UUIDs before join.
    # * Expel instances.
    # * Configure instances that are already joined.
    #   New instances aren't configured here since they don't have
    #   UUIDs before join.

    changed_on_first_call, err = single_edit_topology_call(
        control_console,
        get_replicasets_params,
        new_instances, old_instances,
        new_replicasets, old_replicasets,
        allow_missed_instances,
        healthy_timeout,
    )
    if err is not None:
        return helpers.ModuleRes(failed=True, msg=err)

    # Configure failover_priority and instances that were joined on previous call:
    # * Edit failover_priority of replicasets if it's needed.
    # * Configure instances that weren't configured on first `edit_topology` call.

    changed_on_second_call, err = single_edit_topology_call(
        control_console,
        get_replicasets_params_for_changing_failover_priority,
        new_instances, old_instances,
        new_replicasets, old_replicasets,
        allow_missed_instances,
        healthy_timeout,
    )
    if err is not None:
        return helpers.ModuleRes(failed=True, msg=err)

    return helpers.ModuleRes(changed=changed_on_first_call or changed_on_second_call)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, edit_topology)
