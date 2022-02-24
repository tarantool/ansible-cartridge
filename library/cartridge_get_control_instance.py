#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'module_hostvars': {'required': True, 'type': 'dict'},
    'cluster_disabled_instances': {'required': True, 'type': 'list'},
    'play_hosts': {'required': True, 'type': 'list'},
    'console_sock': {'required': True, 'type': 'str'},
    'app_name': {'required': True, 'type': 'str'},
    'leader_only': {'required': False, 'type': 'bool', 'default': False},
}

GET_TWOPHASE_COMMIT_VERSION_TIMEOUT = 60


def get_membership_members(control_console):
    members, err = control_console.eval_res_err('''
        return require('membership').members()
    ''')
    if err is not None:
        return None, "Impossible to get membership members: %s" % err
    if not members:
        return None, "No members in membership"

    return members, None


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


def candidate_is_ok(uri, names_by_uris, module_hostvars, cluster_disabled_instances):
    instance_name = names_by_uris[uri]
    if instance_name in cluster_disabled_instances:
        return False

    instance_vars = module_hostvars[instance_name]
    return helpers.is_enabled(instance_vars)


def get_control_instance_name(
    module_hostvars,
    cluster_disabled_instances,
    play_hosts,
    control_console,
    leader_only=False,
):
    members, err = get_membership_members(control_console)
    if err is not None:
        return None, err
    leaders, err = helpers.get_active_leaders(control_console)
    if err is not None:
        return None, err

    leaders_uuid = set(leaders.values())

    alien_members_uris = []
    members_without_uuid = []
    members_by_uuid = {}

    for uri, member in sorted(members.items()):
        if not member:
            # it's impossible :)
            alien_members_uris.append(uri)
            continue

        member['uri'] = uri
        member_payload = member.get('payload')
        member_incarnation = member.get('incarnation')
        member_status = member.get('status')

        if not member_incarnation or not member_status or not member_payload or not member_payload.get('alias'):
            # it's possible for old instances, but it can be an error
            alien_members_uris.append(uri)
            continue

        member_uuid = member_payload.get('uuid')
        if not member_uuid:
            members_without_uuid.append(member)
            continue

        if leader_only and member_uuid not in leaders_uuid:
            continue

        existing_member = members_by_uuid.get(member_uuid)
        if existing_member and existing_member['incarnation'] > member_incarnation:
            # ignore it, because it's old
            continue

        members_by_uuid[member_uuid] = member

    if alien_members_uris:
        helpers.warn('Incorrect members with the following URIs ignored: %s' % ', '.join(alien_members_uris))

    alive_instances_uris = set()
    joined_instances_uris = set()
    not_joined_instances_uris = set()
    to_be_joined_instances = set()

    names_by_uris = {}

    all_correct_members = list(members_by_uuid.values()) + members_without_uuid
    for member in all_correct_members:
        uri = member['uri']
        status = member['status']
        alias = member['payload']['alias']
        uuid = member['payload'].get('uuid')

        instance_vars = module_hostvars.get(alias)
        if instance_vars is None and status != 'left':
            return None, "Membership contains instance '%s' that isn't described in inventory" % alias

        names_by_uris[uri] = alias

        if status == 'alive':
            alive_instances_uris.add(uri)

        if uuid is not None:
            joined_instances_uris.add(uri)
        else:
            not_joined_instances_uris.add(uri)
            if alias in play_hosts and instance_vars.get('replicaset_alias') is not None:
                to_be_joined_instances.add(uri)

    if joined_instances_uris:
        # If there is at least one joined instance,
        # we should use any alive one of them as control instance.
        candidates_uris = joined_instances_uris.intersection(alive_instances_uris)

        if not candidates_uris:
            return None, "There is no alive joined instances in the cluster"
    elif to_be_joined_instances:
        # There are no joined instances, but some unjoined instances
        # have replicaset_alias set.
        # One of this instances that is alive should be used for join
        # and cluster configuration.
        candidates_uris = to_be_joined_instances.intersection(alive_instances_uris)

        if not candidates_uris:
            return None, "There is no alive instances that should be be joined"
    else:
        # There are no joined instances and instances that
        # have replicaset_alias set.
        # One of this instances that is alive should be used for join
        # and cluster configuration.
        candidates_uris = not_joined_instances_uris.intersection(alive_instances_uris)

        if not candidates_uris:
            return None, "There is no alive instances in the cluster"

    # filter out instances that are marked to be expelled
    candidates_uris = list(filter(
        lambda uri: candidate_is_ok(uri, names_by_uris, module_hostvars, cluster_disabled_instances),
        candidates_uris
    ))

    if not candidates_uris:
        return None, "Not found any instance that can be used to manage cluster"

    candidates_uris = list(sorted(candidates_uris))

    # Find instance that uses the lowest version of two-phase commit API
    twophase_commit_versions, err = get_twophase_commit_versions(control_console, candidates_uris)
    if err is not None:
        return None, "Failed to check instances two-phase commit version: %s" % err

    idx = twophase_commit_versions.index(min(twophase_commit_versions))
    control_instance_uri = candidates_uris[idx]

    control_instance_name = names_by_uris[control_instance_uri]

    return control_instance_name, None


def get_control_instance(params):
    module_hostvars = params['module_hostvars']
    cluster_disabled_instances = params['cluster_disabled_instances']
    play_hosts = params['play_hosts']
    console_sock = params['console_sock']
    app_name = params['app_name']
    leader_only = params.get('leader_only', False)

    control_console = helpers.get_control_console(console_sock)

    control_instance_name, err = get_control_instance_name(
        module_hostvars, cluster_disabled_instances, play_hosts, control_console, leader_only
    )
    if err is not None:
        return helpers.ModuleRes(failed=True, msg=err)

    # in the ideal imagined world we could just use
    # instance_vars['instance_info'], but if control instance is not
    # in play_hosts, instance_info isn't computed for it
    instance_vars = module_hostvars[control_instance_name]

    run_dir = instance_vars.get('cartridge_run_dir')
    control_instance_console_sock = helpers.get_instance_console_sock(
        run_dir, app_name, control_instance_name,
    )

    http_port = instance_vars.get('config', {}).get('http_port')

    return helpers.ModuleRes(changed=False, fact={
        'name': control_instance_name,
        'console_sock': control_instance_console_sock,
        'http_port': http_port,
    })


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_control_instance)
