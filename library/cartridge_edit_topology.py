#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule

from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console
from ansible.module_utils.helpers import is_expelled, is_stateboard

argument_spec = {
    'hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
    'console_sock': {'required': True, 'type': 'str'},
}


format_replicaset_func = '''
local function format_replicaset(r)
    local instances = {}
    for _, s in ipairs(r.servers) do
        if s.alias ~= nil then
            table.insert(instances, s.alias)
        end
    end

    return {
        uuid = r.uuid,
        alias = r.alias,
        roles = r.roles,
        all_rw = r.all_rw,
        weight = r.weight,
        vshard_group = r.vshard_group,
        instances = instances,
    }
end'''

format_server_func = '''
local function format_server(s)
    local replicaset_uuid
    if s.replicaset ~= nil then
        replicaset_uuid = s.replicaset.uuid
    end

    return {
        uuid = s.uuid,
        uri = s.uri,
        alias = s.alias,
        replicaset_uuid = replicaset_uuid,
    }
end'''

get_replicasets_func_body = '''
%s

local replicasets = require('cartridge').admin_get_replicasets()
local ret = {}

for _, r in ipairs(replicasets) do
    if r.alias ~= nil then
        ret[r.alias] = format_replicaset(r)
    end
end

return ret
''' % format_replicaset_func

get_instances_func_body = '''
%s

local servers = require('cartridge').admin_get_servers()
local ret = {}

for _, s in ipairs(servers) do
    if s.alias ~= nil then
        ret[s.alias] = format_server(s)
    end
end

return ret
''' % format_server_func

edit_topology_func_body = '''
%s
%s

local res, err = require('cartridge').admin_edit_topology(...)

if err ~= nil then
    return nil, err
end

local ret = {
    replicasets = {},
    servers = {},
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
''' % (format_replicaset_func, format_server_func)


def get_cluster_instances(control_console):
    instances, _ = control_console.eval_res_err(get_instances_func_body)

    return instances


def get_configured_replicasets(hostvars, play_hosts):
    replicasets = {}
    for instance_name, instance_vars in hostvars.items():
        if instance_name not in play_hosts:
            continue

        if is_expelled(instance_vars) or is_stateboard(instance_vars):
            continue

        if 'replicaset_alias' in instance_vars:
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


def get_instances_to_expel(hostvars, play_hosts):
    instances_to_expel = [
        instance_name for instance_name in play_hosts
        if not is_stateboard(hostvars[instance_name]) and is_expelled(hostvars[instance_name])
    ]

    return instances_to_expel


def get_cluster_replicasets(control_console):
    cluster_replicasets, _ = control_console.eval_res_err(get_replicasets_func_body)

    if not cluster_replicasets:
        cluster_replicasets = dict()

    return cluster_replicasets


def add_edit_replicaset_param_if_required(edit_replicaset_params, replicaset, cluster_replicaset, param_name):
    if replicaset.get(param_name) is None:
        return

    if cluster_replicaset is not None:
        if param_name == 'roles':
            if set(replicaset.get('roles', [])) == set(cluster_replicaset.get('roles', [])):
                return

        if replicaset.get(param_name) == cluster_replicaset.get(param_name):
            return

    edit_replicaset_params[param_name] = replicaset.get(param_name)


def get_edit_replicaset_params(replicaset, cluster_replicaset, cluster_instances):
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

    edit_replicaset_params = {}

    if cluster_replicaset is not None:
        edit_replicaset_params['uuid'] = cluster_replicaset['uuid']
    else:
        edit_replicaset_params['alias'] = replicaset['alias']

    for param_name in ['weight', 'vshard_group', 'all_rw', 'roles']:
        add_edit_replicaset_param_if_required(
            edit_replicaset_params, replicaset, cluster_replicaset, param_name
        )

    current_instances = []
    if cluster_replicaset is not None:
        current_instances = cluster_replicaset.get('instances')

    instances_to_join = list(
        set(replicaset['instances']) - set(current_instances)
    )

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
            if replicaset['failover_priority']:
                if not all([s in cluster_instances for s in replicaset['failover_priority']]):
                    instances_not_in_cluster_str = ', '.join([
                        s for s in replicaset['failover_priority'] if s not in cluster_instances
                    ])
                    err = "Some of instances specified in failover_priority aren't found in cluster: %s"
                    return None, err % instances_not_in_cluster_str

                first_instances_to_join = [
                    instance_name for instance_name in replicaset['failover_priority']
                    if instance_name in instances_to_join
                ]

                instances_to_join = first_instances_to_join + [
                    instance for instance in instances_to_join if instance not in first_instances_to_join
                ]

        if not all([s in cluster_instances for s in instances_to_join]):
            instances_not_in_cluster_str = ', '.join([
                s for s in instances_to_join if s not in cluster_instances
            ])

            return None, "Some of replicaset instances aren't found in cluster: %s " % instances_not_in_cluster_str

        edit_replicaset_params['join_servers'] = [
            {'uri': cluster_instances[s]['uri']}
            for s in instances_to_join
        ]

    if 'uuid' in edit_replicaset_params and len(edit_replicaset_params) == 1:
        # replicaset is already exists
        # and all parameters are the same as configured
        return None, None

    return edit_replicaset_params, None


def get_edit_replicasets_params(replicasets, cluster_replicasets, cluster_instances):
    edit_replicasets_params = []

    for _, replicaset in replicasets.items():
        cluster_replicaset = cluster_replicasets.get(replicaset['alias'])

        edit_replicaset_params, err = get_edit_replicaset_params(
            replicaset, cluster_replicaset, cluster_instances
        )

        if err is not None:
            return None, "Failed to get edit topology params for replicaset %s: %s" % (
                replicaset['alias'], err
            )

        if edit_replicaset_params is not None:
            edit_replicasets_params.append(edit_replicaset_params)

    return edit_replicasets_params, None


def get_edit_servers_params(instances_to_expel, cluster_instances):
    edit_servers_params = [
        {
            'uuid': cluster_instances[instance_name]['uuid'],
            'expelled': True,
        }
        for instance_name in instances_to_expel
        if instance_name in cluster_instances and cluster_instances[instance_name].get('uuid') is not None
    ]

    return edit_servers_params


def get_edit_topology_params(replicasets, cluster_replicasets, instances_to_expel, cluster_instances):
    edit_topology_params = {}

    edit_replicasets_params, err = get_edit_replicasets_params(replicasets, cluster_replicasets, cluster_instances)
    if err is not None:
        return None, err

    if edit_replicasets_params:
        edit_topology_params['replicasets'] = edit_replicasets_params

    edit_servers_params = get_edit_servers_params(instances_to_expel, cluster_instances)
    if edit_servers_params:
        edit_topology_params['servers'] = edit_servers_params

    return edit_topology_params, None


def get_edit_failover_priority_params(replicasets, cluster_replicasets, cluster_instances):
    edit_topology_params = {}
    edit_replicasets_params = []

    for alias, cluster_replicaset in cluster_replicasets.items():
        if alias not in replicasets:
            continue

        failover_priority = replicasets[alias].get('failover_priority')
        if failover_priority is None:
            continue

        if cluster_replicaset['instances'][:len(failover_priority)] != failover_priority:
            failover_priority_uuids = [
                cluster_instances[instance_name]['uuid'] for instance_name in failover_priority
                if instance_name in cluster_instances  # false if instance is expelled
            ]

            edit_replicasets_params.append({
                'uuid': cluster_replicaset['uuid'],
                'failover_priority': failover_priority_uuids,
            })

    if edit_replicasets_params:
        edit_topology_params['replicasets'] = edit_replicasets_params

    return edit_topology_params


def edit_topology(params):
    console_sock = params['console_sock']
    hostvars = params['hostvars']
    play_hosts = params['play_hosts']

    replicasets = get_configured_replicasets(hostvars, play_hosts)
    instances_to_expel = get_instances_to_expel(hostvars, play_hosts)

    if not replicasets and not instances_to_expel:
        return ModuleRes(success=True, changed=False)

    control_console = get_control_console(console_sock)
    cluster_instances = get_cluster_instances(control_console)

    # call edit_topology once
    cluster_replicasets = get_cluster_replicasets(control_console)
    edit_topology_params, err = get_edit_topology_params(
        replicasets, cluster_replicasets, instances_to_expel, cluster_instances
    )
    if err is not None:
        return ModuleRes(success=False, msg="Failed to collect edit topology params: %s" % err)

    topology_changed = False

    if edit_topology_params:
        res, err = control_console.eval_res_err(edit_topology_func_body, edit_topology_params)
        if err is not None:
            return ModuleRes(success=False, msg="Failed to edit topology: %s" % err)

        topology_changed = True
        edited_replicasets = res['replicasets']
        edited_instances = res['servers']

        # update replicasets
        for alias, replicaset in edited_replicasets.items():
            cluster_replicasets[alias] = replicaset

        # update instances
        for alias, instance in edited_instances.items():
            cluster_instances[alias] = instance

    # change failover priority if needed
    edit_topology_params = get_edit_failover_priority_params(replicasets, cluster_replicasets, cluster_instances)
    if edit_topology_params:
        res, err = control_console.eval_res_err(edit_topology_func_body, edit_topology_params)
        if err is not None:
            return ModuleRes(success=False, msg="Failed to edit failover priority: %s" % err)

        topology_changed = True
        cluster_replicasets = res['replicasets']

    return ModuleRes(success=True, changed=topology_changed)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = edit_topology(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, **res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
