#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console

import time

argument_spec = {
    'replicaset': {'required': True, 'type': 'dict'},
    'control_sock': {'required': True, 'type': 'str'},
}


def get_all_instances_info(control_console):
    servers = control_console.eval('''
        local instances = require('cartridge').admin_get_servers()
        local res = {}
        for _, i in ipairs(instances) do
            local replicaset = require('json').NULL
            if i.replicaset then
                replicaset = {
                    uuid = i.replicaset.uuid,
                    alias = i.replicaset.alias,
                    roles = i.replicaset.roles,
                }
            end
            table.insert(res, {
                uuid = i.uuid,
                uri = i.uri,
                alias = i.alias,
                status = i.status,
                replicaset = replicaset,
            })
        end
        return res
    ''')

    return servers


def get_replicaset_info(control_console, name):
    # Get all replicasets
    replicasets = control_console.eval('''
        local replicasets = require('cartridge').admin_get_replicasets()
        local res = {}
        for _, r in ipairs(replicasets) do
            local servers = {}
            for _, s in ipairs(r.servers) do
                table.insert(servers, { alias = s.alias })
            end

            table.insert(res, {
                uuid = r.uuid,
                alias = r.alias,
                status = r.status,
                roles = r.roles,
                master = { alias = r.master.alias },
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


def wait_for_replicaset_is_healthy(control_console, replicaset_alias):
    delay = 0.5
    timeout = 10
    time_start = time.time()

    while True:
        now = time.time()
        if now > time_start + timeout:
            return False

        replicaset_info = get_replicaset_info(
            control_console,
            replicaset_alias
        )

        if replicaset_info is None:
            errmsg = '"{}" replicaset was not found in cluster'.format(replicaset_alias)
            return ModuleRes(success=False, msg=errmsg)

        if replicaset_info['status'] == 'healthy':
            return True

        time.sleep(delay)


def create_replicaset(control_console, params):
    replicaset_alias = params['replicaset']['alias']
    replicaset_leader = params['replicaset']['leader']
    replicaset_roles = params['replicaset']['roles']
    replicaset_instances = params['replicaset']['instances']

    # Check if all instances are started and not configured
    instances_info = get_all_instances_info(control_console)
    instances_info = {i['alias']: i for i in instances_info}  # make it dict

    if replicaset_leader not in instances_info:
        errmsg = 'Leader "{}" (replicaset "{}") not found is cluster. Make sure it was started'.format(
            replicaset_leader, replicaset_alias
        )
        return ModuleRes(success=False, msg=errmsg)

    # Cerate replicaset (join leader)
    leader_instance_info = instances_info[replicaset_leader]
    res = control_console.eval('''
        local ok, err = require('cartridge').admin_join_server({{
            uri = '{}',
            roles = {{ {} }},
            replicaset_alias = '{}',
        }})
        return {{
            ok = ok and true or false,
            err = err and err.err or require('json').NULL
        }}
    '''.format(
        leader_instance_info['uri'],
        ', '.join(['"{}"'.format(role) for role in replicaset_roles]),
        replicaset_alias
    ))
    if not res['ok']:
        errmsg = 'Failed to create "{}" replicaset: {}'.format(replicaset_alias, res['err'])
        return ModuleRes(success=False, msg=errmsg)

    # Wait for replicaset is healthy
    if not wait_for_replicaset_is_healthy(control_console, replicaset_alias):
        errmsg = 'Replicaset "{}" is not healthy'.format(replicaset_alias)
        return ModuleRes(success=False, msg=errmsg)

    # Get replicaset UUID
    replicaset_info = get_replicaset_info(control_console, replicaset_alias)
    replicaset_uuid = replicaset_info['uuid']

    # Remove leader from instances list
    replicaset_instances.remove(replicaset_leader)

    # Join other instances
    for replicaset_instance in replicaset_instances:
        if replicaset_instance not in instances_info:
            errmsg = 'Instance "{}" (replicaset "{}") not found is cluster. Make sure it was started'.format(
                replicaset_instance, replicaset_alias
            )
            return ModuleRes(success=False, msg=errmsg)

        replicaset_instance_info = instances_info[replicaset_instance]
        res = control_console.eval('''
            local ok, err = require('cartridge').admin_join_server({{
                uri = '{}',
                replicaset_uuid = '{}',
            }})
            return {{
                ok = ok and true or false,
                err = err and err.err or require('json').NULL
            }}
        '''.format(
            replicaset_instance_info['uri'],
            replicaset_uuid
        ))

        if not res['ok']:
            errmsg = 'Failed to join "{}": {}'.format(replicaset_instance, res['err'])
            return ModuleRes(success=False, msg=errmsg)

        # Wait for replicaset is healthy
        if not wait_for_replicaset_is_healthy(control_console, replicaset_alias):
            errmsg = 'Replicaset "{}" is not healthy'.format(replicaset_alias)
            return ModuleRes(success=False, msg=errmsg)

    return ModuleRes(success=True, changed=True)


def manage_replicaset(params):
    control_console = get_control_console(params['control_sock'])

    # Check if replicaset is already created
    replicaset_info = get_replicaset_info(
        control_console,
        params['replicaset']['alias']
    )

    if replicaset_info is None:
        return create_replicaset(control_console, params)

    return ModuleRes(success=True, changed=False)


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
