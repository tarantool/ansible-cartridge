#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console
from ansible.module_utils.helpers import get_all_cluster_instances

import time

argument_spec = {
    'replicaset': {'required': True, 'type': 'dict'},
    'control_sock': {'required': True, 'type': 'str'},
    'healthy_timeout': {'required': False, 'default': 10, 'type': 'int'},
}


def get_cluster_replicaset(control_console, name):
    # Get all replicasets
    replicasets = control_console.eval('''
        local replicasets = require('cartridge').admin_get_replicasets()
        local res = {}
        for _, r in ipairs(replicasets) do
            local servers = {}
            for _, s in ipairs(r.servers) do
                table.insert(servers, { alias = s.alias, priority = s.priority })
            end

            table.insert(res, {
                uuid = r.uuid or box.NULL,
                alias = r.alias or box.NULL,
                status = r.status or box.NULL,
                roles = r.roles or box.NULL,
                all_rw = r.all_rw or box.NULL,
                weight = r.weight or box.NULL,
                vshard_group = r.vshard_group or box.NULL,
                servers = servers,
            })
        end
        return res
    ''')

    # Find by name
    for replicaset in replicasets:
        if replicaset['alias'] == name:
            return replicaset

    return None


def wait_for_replicaset_is_healthy(control_console, replicaset_alias, timeout):
    delay = 0.5
    time_start = time.time()

    while True:
        now = time.time()
        if now > time_start + timeout:
            return False

        cluster_replicaset = get_cluster_replicaset(
            control_console,
            replicaset_alias
        )

        if cluster_replicaset is None:
            return False

        if cluster_replicaset['status'] == 'healthy':
            return True

        time.sleep(delay)


def aliases_in_priority_order(replicaset_servers):
    return [s['alias'] for s in sorted(replicaset_servers, key=lambda x: x['priority'])]


def cluster_replicasets_are_equal(rpl1, rpl2):
    return rpl1['uuid'] == rpl2['uuid'] \
        and rpl1['alias'] == rpl2['alias'] \
        and rpl1['all_rw'] == rpl2['all_rw'] \
        and rpl1['weight'] == rpl2['weight'] \
        and rpl1['vshard_group'] == rpl2['vshard_group'] \
        and set(rpl1['roles']) == set(rpl2['roles']) \
        and aliases_in_priority_order(rpl1['servers']) == aliases_in_priority_order(rpl2['servers'])


def edit_replicaset(control_console, cluster_instances,
                    alias=None, uuid=None,
                    join_servers=None,
                    failover_priority=None,
                    roles=None,
                    all_rw=None,
                    weight=None,
                    vshard_group=None):

    assert (alias is not None) ^ (uuid is not None)

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

    replicaset_params = []
    if alias is not None:
        replicaset_params.append('alias = "{}"'.format(alias))

    if uuid is not None:
        replicaset_params.append('uuid = "{}"'.format(uuid))

    if join_servers:
        replicaset_params.append('join_servers = {{ {} }}'.format(
            ', '.join([
                '{{ uri = "{}" }}'.format(cluster_instances[i]['uri'])
                for i in join_servers
                if i in cluster_instances
            ])
        ))

    if failover_priority:
        replicaset_params.append('failover_priority = {{ {} }}'.format(
            ', '.join([
                '"{}"'.format(cluster_instances[i]['uuid'])
                for i in failover_priority
                if i in cluster_instances
            ])
        ))

    if roles:
        replicaset_params.append('roles = {{ {} }}'.format(', '.join('"{}"'.format(role) for role in roles)))

    if all_rw is not None:
        replicaset_params.append('all_rw = {}'.format('true' if all_rw else 'false'))

    if weight is not None:
        replicaset_params.append('weight = {}'.format(weight))

    if vshard_group is not None:
        replicaset_params.append('vshard_group = "{}"'.format(vshard_group))

    res = control_console.eval('''
        local res, err = require('cartridge').admin_edit_topology({{
            replicasets = {{
                {{
                    {}
                }},
            }}
        }})
        if not res then
            return {{
                ret = box.NULL,
                err = err and err.err or box.NULL,
            }}
        end
        local ret = {{
            replicasets = {{ }},
            servers = {{ }},
        }}
        for _, r in ipairs(res.replicasets or {{}}) do
            local servers = {{}}
            for _, s in ipairs(r.servers) do
                table.insert(servers, {{ alias = s.alias, priority = s.priority, uuid = s.uuid }})
            end
            table.insert(ret.replicasets, {{
                uuid = r.uuid or box.NULL,
                alias = r.alias or box.NULL,
                status = r.status or box.NULL,
                all_rw = r.all_rw or box.NULL,
                weight = r.weight or box.NULL,
                roles = r.roles or box.NULL,
                vshard_group = r.vshard_group or box.NULL,
                servers = servers,
            }})
        end
        for _, s in ipairs(res.servers or {{}}) do
            local replicaset = box.NULL
            if s.replicaset then
                replicaset = {{
                    uuid = s.replicaset.uuid or box.NULL,
                    alias = s.replicaset.alias or box.NULL,
                    roles = s.replicaset.roles or box.NULL,
                }}
            end
            table.insert(ret.servers, {{
                uuid = s.uuid or box.NULL,
                uri = s.uri or box.NULL,
                alias = s.alias or box.NULL,
                status = s.status or box.NULL,
                replicaset = replicaset or box.NULL,
            }})
        end
        return {{
            ret = ret,
            err = box.NULL,
         }}
    '''.format(', '.join(replicaset_params)))

    return res['ret'], res['err']


def create_replicaset(control_console, params):
    replicaset_alias = params['replicaset']['alias']
    replicaset_failover_priority = params['replicaset']['failover_priority']
    replicaset_roles = params['replicaset']['roles']
    replicaset_instances = params['replicaset']['instances']
    replicaset_all_rw = params['replicaset']['all_rw'] if 'all_rw' in params['replicaset'] else None
    replicaset_weight = params['replicaset']['weight'] if 'weight' in params['replicaset'] else None
    replicaset_vshard_group = params['replicaset'].get('vshard_group', None)

    healthy_timeout = params['healthy_timeout']

    cluster_instances = get_all_cluster_instances(control_console)
    cluster_instances = {i['alias']: i for i in cluster_instances}  # make it dict

    replicaset_leader = replicaset_failover_priority[0]

    if replicaset_leader not in cluster_instances:
        errmsg = 'Leader "{}" (replicaset "{}") not found is cluster. Make sure it was started'.format(
            replicaset_leader, replicaset_alias
        )
        return ModuleRes(success=False, msg=errmsg)

    # Cerate replicaset (join leader)
    res, err = edit_replicaset(control_console, cluster_instances,
                               alias=replicaset_alias,
                               join_servers=[replicaset_leader],
                               roles=replicaset_roles,
                               all_rw=replicaset_all_rw,
                               weight=replicaset_weight,
                               vshard_group=replicaset_vshard_group)

    if not res:
        errmsg = 'Failed to create "{}" replicaset: {}'.format(replicaset_alias, err)
        return ModuleRes(success=False, msg=errmsg)

    for i in res['servers']:
        cluster_instances[i['alias']] = i

    # Wait for replicaset is healthy
    if not wait_for_replicaset_is_healthy(control_console, replicaset_alias, healthy_timeout):
        errmsg = 'Replicaset "{}" is not healthy'.format(replicaset_alias)
        return ModuleRes(success=False, msg=errmsg)

    # Get replicaset UUID
    cluster_replicaset = get_cluster_replicaset(control_console, replicaset_alias)
    replicaset_uuid = cluster_replicaset['uuid']

    # Remove leader from instances list
    replicaset_instances.remove(replicaset_leader)

    # Join other instances
    for replicaset_instance in replicaset_instances:
        if replicaset_instance not in cluster_instances:
            errmsg = 'Instance "{}" (replicaset "{}") not found is cluster. Make sure it was started'.format(
                replicaset_instance, replicaset_alias
            )
            return ModuleRes(success=False, msg=errmsg)

        res, err = edit_replicaset(control_console, cluster_instances,
                                   uuid=replicaset_uuid,
                                   join_servers=[replicaset_instance])
        if not res:
            errmsg = 'Failed to join "{}" to replicaset "{}": {}'.format(replicaset_instance, replicaset_alias, err)
            return ModuleRes(success=False, msg=errmsg)

        for i in res['servers']:
            cluster_instances[i['alias']] = i

        # Wait for replicaset is healthy
        if not wait_for_replicaset_is_healthy(control_console, replicaset_alias, healthy_timeout):
            errmsg = 'Replicaset "{}" is not healthy'.format(replicaset_alias)
            return ModuleRes(success=False, msg=errmsg)

    if len(replicaset_failover_priority) > 1:
        # Set failover priority
        res, err = edit_replicaset(control_console, cluster_instances,
                                   uuid=replicaset_uuid,
                                   failover_priority=replicaset_failover_priority)
        if not res:
            errmsg = 'Failed to set failover priority in "{}" replicaset: {}'.format(replicaset_alias, err)
            return ModuleRes(success=False, msg=errmsg)

    return ModuleRes(success=True, changed=True)


def change_replicaset(control_console, params, cluster_replicaset):
    replicaset_alias = params['replicaset']['alias']
    replicaset_roles = params['replicaset']['roles']
    replicaset_failover_priority = params['replicaset']['failover_priority']
    replicaset_instances = params['replicaset']['instances']
    replicaset_all_rw = params['replicaset']['all_rw'] if 'all_rw' in params['replicaset'] else None
    replicaset_weight = params['replicaset']['weight'] if 'weight' in params['replicaset'] else None
    replicaset_vshard_group = params['replicaset'].get('vshard_group', None)

    healthy_timeout = params['healthy_timeout']

    if cluster_replicaset['status'] != 'healthy':
        errmsg = 'Replicaset "{}" is not healthy'.format(replicaset_alias)
        return ModuleRes(success=False, msg=errmsg)

    cluster_instances = get_all_cluster_instances(control_console)
    cluster_instances = {i['alias']: i for i in cluster_instances}  # make it dict

    servers_to_join = list(set(replicaset_instances) - set([s['alias'] for s in cluster_replicaset['servers']]))
    for s in servers_to_join:
        if s not in cluster_instances:
            errmsg = 'Instance "{}" specified in replicaset "{}" is not in cluster. '.format(s, replicaset_alias) + \
                'Make sure that it was started.'
            return ModuleRes(success=False, msg=errmsg)

    for s in replicaset_failover_priority:
        if s not in cluster_instances:
            errmsg = 'Instance "{}" specified in replicaset "{}" is not in cluster. '.format(s, replicaset_alias) + \
                'Make sure that it was started.'
            return ModuleRes(success=False, msg=errmsg)

    if servers_to_join:
        res, err = edit_replicaset(control_console, cluster_instances,
                                   uuid=cluster_replicaset['uuid'],
                                   join_servers=servers_to_join)

        if not res:
            errmsg = 'Failed to edit replicaset "{}": {}'.format(replicaset_alias, err)
            return ModuleRes(success=False, msg=errmsg)

        # Wait for replicaset is healthy
        if not wait_for_replicaset_is_healthy(control_console, replicaset_alias, healthy_timeout):
            errmsg = 'Replicaset "{}" is not healthy'.format(replicaset_alias)
            return ModuleRes(success=False, msg=errmsg)

        for i in res['servers']:
            cluster_instances[i['alias']] = i

    res, err = edit_replicaset(control_console, cluster_instances,
                               uuid=cluster_replicaset['uuid'],
                               roles=replicaset_roles,
                               failover_priority=replicaset_failover_priority,
                               all_rw=replicaset_all_rw,
                               weight=replicaset_weight,
                               vshard_group=replicaset_vshard_group)
    if not res:
        errmsg = 'Failed to edit replicaset "{}": {}'.format(replicaset_alias, err)
        return ModuleRes(success=False, msg=errmsg)

    # Wait for replicaset is healthy
    if not wait_for_replicaset_is_healthy(control_console, replicaset_alias, healthy_timeout):
        errmsg = 'Replicaset "{}" is not healthy'.format(replicaset_alias)
        return ModuleRes(success=False, msg=errmsg)

    edited_cluster_replicaset = get_cluster_replicaset(
        control_console,
        replicaset_alias
    )

    changed = not cluster_replicasets_are_equal(cluster_replicaset, edited_cluster_replicaset)

    return ModuleRes(success=True, changed=changed)


def manage_replicaset(params):
    control_console = get_control_console(params['control_sock'])

    # Check if replicaset is already created
    cluster_replicaset = get_cluster_replicaset(
        control_console,
        params['replicaset']['alias']
    )

    if cluster_replicaset is None:
        return create_replicaset(control_console, params)

    return change_replicaset(control_console, params, cluster_replicaset)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = manage_replicaset(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
