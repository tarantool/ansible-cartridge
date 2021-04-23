#!/usr/bin/env python

import socket

from ansible.module_utils.helpers import Helpers as helpers


argument_spec = {
    'module_hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
    'app_name': {'required': True, 'type': 'str'},
}


CONNECTION_TIMEOUT = 10


def get_alive_not_expelled_instance(params):
    module_hostvars = params['module_hostvars']
    play_hosts = params['play_hosts']
    app_name = params['app_name']

    canditates_by_uris = {}

    for instance_name in play_hosts:
        instance_vars = module_hostvars[instance_name]
        if helpers.is_expelled(instance_vars) or helpers.is_stateboard(instance_vars):
            continue

        instance_config = instance_vars.get('config')
        if instance_config is None:
            continue

        advertise_uri = instance_config['advertise_uri']
        canditates_by_uris[advertise_uri] = instance_name

    alive_not_expelled_instance_name = None
    for uri, instance_name in sorted(canditates_by_uris.items()):
        host, port = uri.rsplit(':', 1)

        try:
            conn = socket.create_connection((host, port), timeout=CONNECTION_TIMEOUT)
            conn.settimeout(CONNECTION_TIMEOUT)
            conn.recv(1024)
        except socket.error:
            continue

        alive_not_expelled_instance_name = instance_name
        break

    if alive_not_expelled_instance_name is None:
        errmsg = "Not found any alive instance that is not expelled and is not a stateboard"
        return helpers.ModuleRes(failed=True, msg=errmsg)

    instance_vars = module_hostvars[alive_not_expelled_instance_name]
    run_dir = instance_vars.get('cartridge_run_dir', helpers.DEFAULT_RUN_DIR)
    console_sock = helpers.get_instance_console_sock(
        run_dir, app_name, alive_not_expelled_instance_name,
    )

    return helpers.ModuleRes(changed=False, fact={
        'name': alive_not_expelled_instance_name,
        'console_sock': console_sock,
    })


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_alive_not_expelled_instance)
