#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes
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


def wait_for_replicaset_is_healthy(control_console, replicaset_name):
    delay = 0.5
    timeout = 5
    while True:
        time_start = time.time()
        now = time.time()
        if now > time_start + timeout:
            return False

        replicaset_info = get_replicaset_info(
            control_console,
            replicaset_name
        )
        if replicaset_info['status'] == 'healthy':
            return True

        time.sleep(delay)


def create_replicaset(control_console, params):
    replicaset = params['replicaset']
    # sanity checks
    if len(replicaset['instances']) == 1 and 'leader' not in replicaset:
        replicaset['leader'] = replicaset['instances'][0]

    if 'leader' not in replicaset:
        return ModuleRes(success=False, msg='Replicaset leader must be specified')

    if replicaset['leader'] not in replicaset['instances']:
        return ModuleRes(success=False, msg='Replicaset leader must be one of replicaset instances')

    # Check if all instances are started and not configured
    instances_info = get_all_instances_info(control_console)
    instances_info = {i['alias']: i for i in instances_info}  # make it dict

    # Cerate replicaset (join leader)
    leader_instance_info = instances_info[replicaset['leader']]
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
        ', '.join(['"{}"'.format(role) for role in params['replicaset']['roles']]),
        replicaset['name']
    ))

    # Wait for replicaset is healthy
    if not wait_for_replicaset_is_healthy(control_console, replicaset['name']):
        errmsg = 'Replicaset "{}" is not healthy'.format(replicaset['name'])
        return ModuleRes(success=False, msg=errmsg)

    # Get replicaset UUID
    replicaset_info = get_replicaset_info(control_console, params['replicaset']['name'])

    replicaset_uuid = replicaset_info['uuid']

    # Remove leader from instances list
    replicaset_instances = replicaset['instances']
    replicaset_instances.remove(replicaset['leader'])

    # Join other instances
    for replicaset_instance in replicaset_instances:
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
            errmsg = 'Failed to join "{}": {}'.format(replicaset_instance_info['name'], res['err'])
            return ModuleRes(success=False, msg=errmsg)

        # Wait for replicaset is healthy
        if not wait_for_replicaset_is_healthy(control_console, replicaset['name']):
            errmsg = 'Replicaset "{}" is not healthy'.format(replicaset['name'])
            return ModuleRes(success=False, msg=errmsg)

    return ModuleRes(success=True, changed=True, meta={'instances': instances_info, 'join_res': res})


def setup_replicaset(params):
    # Sanity checks
    if 'name' not in params['replicaset']:
        return ModuleRes(success=False, msg='Replicaset name must be specified')

    if 'instances' not in params['replicaset']:
        return ModuleRes(success=False, msg='Replicaset instances must be specified')

    if 'roles' not in params['replicaset']:
        return ModuleRes(success=False, msg='Replicaset roles must be specified')

    if not params['replicaset']['roles']:
        return ModuleRes(success=False, msg='Replicaset must have at least one role')

    control_console = get_control_console(params['control_sock'])

    # Check if replicaset is already created
    replicaset_info = get_replicaset_info(
        control_console,
        params['replicaset']['name']
    )

    if replicaset_info is None:
        return create_replicaset(control_console, params)

    return ModuleRes(success=True, changed=False)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = setup_replicaset(module.params)

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
