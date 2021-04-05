#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'module_hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
    'console_sock': {'required': True, 'type': 'str'},
    'app_name': {'required': True, 'type': 'str'},
}

GET_TWOPHASE_COMMIT_VERSION_TIMEOUT = 60


def get_twophase_commit_versions(control_console, advertise_uris):
    versions, err = control_console.eval_res_err('''
        local fiber_clock = require('fiber').clock
        local pool = require('cartridge.pool')

        local uris, timeout = ...

        local deadline = fiber_clock() + timeout

        local connections = {}
        for i, uri in ipairs(uris) do
            local conn, err = pool.connect(uri)
            if err ~= nil then
                return nil, tostring(err)
            end

            table.insert(connections, conn)
        end

        local futures = {}
        for _, conn in ipairs(connections) do
            local future = conn:eval([[
                local twophase_version = require('cartridge.twophase').VERSION
                if twophase_version ~= nil then
                    return twophase_version
                end

                if rawget(_G, '__cartridge_upload_begin') ~= nil then
                    return 2
                else
                    return 1
                end
            ]], nil, {is_async = true})

            table.insert(futures, future)
        end

        local versions = {}

        for _, future in ipairs(futures) do
            local wait_timeout = deadline - fiber_clock()
            if wait_timeout < 0 then
                wait_timeout = 0
            end

            local result, err = future:wait_result(wait_timeout)
            if err ~= nil then
                return nil, tostring(err)
            end

            local version = result[1]
            table.insert(versions, version)
        end

        return versions
    ''', advertise_uris, GET_TWOPHASE_COMMIT_VERSION_TIMEOUT)

    return versions, err


def get_control_instance(params):
    module_hostvars = params['module_hostvars']
    play_hosts = params['play_hosts']
    console_sock = params['console_sock']
    app_name = params['app_name']

    control_console = helpers.get_control_console(console_sock)
    control_instance_candidates = []

    members, _ = control_console.eval_res_err('''
        return require('membership').members()
    ''')

    for uri, member in sorted(members.items()):
        if 'payload' not in member or not member['payload']:
            return helpers.ModuleRes(failed=True, msg='Instance %s does not contain payload' % uri)

        if member.get('status') != 'alive':
            continue

        member_payload = member['payload']
        if member_payload.get('uuid') is not None:
            if member_payload.get('alias') is None:
                return helpers.ModuleRes(failed=True, msg='Instance %s payload does not contain alias' % uri)

            instance_name = member_payload['alias']
            if instance_name not in module_hostvars:
                continue

            control_instance_candidates.append(instance_name)

    if not control_instance_candidates:
        for instance_name in play_hosts:
            instance_vars = module_hostvars[instance_name]

            if helpers.is_expelled(instance_vars) or helpers.is_stateboard(instance_vars):
                continue

            if 'replicaset_alias' in instance_vars:
                control_instance_candidates.append(instance_name)

    if not control_instance_candidates:
        errmsg = 'Not found any joined instance or instance to create a replicaset'
        return helpers.ModuleRes(failed=True, msg=errmsg)

    advertise_uris = [
        module_hostvars[instance_name]['config']['advertise_uri']
        for instance_name in control_instance_candidates
    ]

    twophase_commit_versions, err = get_twophase_commit_versions(control_console, advertise_uris)
    if err is not None:
        return helpers.ModuleRes(failed=True, msg=err)

    idx = twophase_commit_versions.index(min(twophase_commit_versions))
    control_instance_name = control_instance_candidates[idx]

    # in the ideal imagined world we could just use
    # instance_vars['instance_info'], but if control instance is not
    # in play_hosts, instance_info isn't computed for it
    instance_vars = module_hostvars[control_instance_name]
    run_dir = instance_vars.get('cartridge_run_dir', helpers.DEFAULT_RUN_DIR)
    control_instance_console_sock = helpers.get_instance_console_sock(
        run_dir, app_name, control_instance_name,
    )

    return helpers.ModuleRes(changed=False, fact={
        'name': control_instance_name,
        'console_sock': control_instance_console_sock,
    })


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_control_instance)
