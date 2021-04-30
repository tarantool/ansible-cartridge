#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'allowed_states': {'required': True, 'type': 'list'},
}


def check_members_alive(params):
    console_sock = params['console_sock']
    allowed_states = params['allowed_states']

    control_console = helpers.get_control_console(console_sock)

    bad_members, err = control_console.eval_res_err('''
        local fun = require('fun')
        local membership = require('membership')

        local cartridge_topology = require('cartridge.topology')
        local confapplier = require('cartridge.confapplier')

        local topology_cfg = confapplier.get_readonly('topology')

        if topology_cfg == nil then
            return nil, "Instances aren't joined to cluster yet"
        end

        local allowed_states = ...
        local bad_members = {}

        for _it, instance_uuid, server in fun.filter(cartridge_topology.not_disabled, topology_cfg.servers) do
            local member = membership.get_member(server.uri) or {}

            if (member.payload.uuid ~= instance_uuid) then
                table.insert(bad_members, string.format(
                    '%s uuid mismatch: expected %s, have %s',
                    server.uri, instance_uuid, member.payload.uuid
                ))
            elseif (member.status ~= 'alive') then
                table.insert(bad_members, string.format(
                    '%s status is %s',
                    server.uri, member.status
                ))
            elseif allowed_states ~= nil and next(allowed_states) ~= nil then
                local member_state = member.payload.state
                if fun.index(member_state, allowed_states) == nil then
                    table.insert(bad_members, string.format(
                    '%s state is %s',
                    server.uri, member_state
                ))
                end
            end
        end

        return bad_members
    ''', allowed_states)

    if err is not None:
        return helpers.ModuleRes(failed=True, msg=err)

    if bad_members:
        return helpers.ModuleRes(failed=True, msg="Some instances aren't alive: %s" % ', '.join(sorted(bad_members)))

    return helpers.ModuleRes(changed=False)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, check_members_alive)
