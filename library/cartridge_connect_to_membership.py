#!/usr/bin/python

import math
import pkgutil

if pkgutil.find_loader('ansible.module_utils.helpers'):
    import ansible.module_utils.helpers as helpers
else:
    import module_utils.helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
}

BATCH_SIZE = 32


def connect_instances(control_console, play_hosts, instance_names, advertise_uris):
    connect_errors, _ = control_console.eval_res_err('''
        local advertise_uris = ...

        local cartridge = require('cartridge')
        local fiber = require('fiber')

        local count = 0
        local channel = fiber.channel()

        for _, advertise_uri in ipairs(advertise_uris) do
            count = count + 1

            fiber.create(function()
                local _, err = cartridge.admin_probe_server(advertise_uri)
                channel:put({
                    advertise_uri = advertise_uri,
                    err = err and err.err or err,
                })
            end)
        end

        local errors = {}
        for _ = 1, count do
            local res = channel:get(60)
            if res == nil then
                table.insert(errors, {msg = 'Failed to get probe result: timeout'})
                break
            end
            if res.err ~= nil then
                table.insert(errors, {
                    msg = ("Failed to probe server '%%s': %s"):format(res.err),
                    advertise_uri = res.advertise_uri,
                })
            end
        end
        return errors
    ''', advertise_uris)

    errors = []
    warnings = []

    for error in connect_errors:
        if not error['advertise_uri']:
            errors.append(error['msg'])
            break

        instance_name = instance_names[error['advertise_uri']]
        msg = error['msg'] % instance_name

        if instance_name in play_hosts:
            errors.append(msg)
        else:
            warnings.append(msg)

    return errors, warnings


def connect_to_membership(params):
    control_console = helpers.get_control_console(params['console_sock'])
    hostvars = params['hostvars']
    play_hosts = params['play_hosts']

    advertise_uris = []
    instance_names = {}

    for instance_name, instance_vars in hostvars.items():
        if helpers.is_expelled(instance_vars) or helpers.is_stateboard(instance_vars):
            continue

        if 'config' not in instance_vars or 'advertise_uri' not in instance_vars['config']:
            continue

        advertise_uri = instance_vars['config']['advertise_uri']
        advertise_uris.append(advertise_uri)
        instance_names[advertise_uri] = instance_name

    warnings = []

    for i in range(int(math.ceil(len(advertise_uris) / BATCH_SIZE))):
        advertise_uris_batch = advertise_uris[i * BATCH_SIZE: (i + 1) * BATCH_SIZE]

        errors, warns = connect_instances(control_console, play_hosts, instance_names, advertise_uris_batch)
        warnings += warns

        if len(errors) > 0:
            return helpers.ModuleRes(failed=True, msg=errors, warnings=warnings)

    return helpers.ModuleRes(changed=False, warnings=warnings)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, connect_to_membership)
