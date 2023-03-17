#!/usr/bin/env python

import socket
import ssl

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'module_hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
    'cluster_disabled_instances': {'required': True, 'type': 'list'},
    'app_name': {'required': True, 'type': 'str'},
}

CONNECTION_TIMEOUT = 3


def get_alive_not_expelled_instance(params):
    module_hostvars = params['module_hostvars']
    cluster_disabled_instances = params['cluster_disabled_instances']
    play_hosts = params['play_hosts']
    app_name = params['app_name']

    warnings = []
    is_ssl = False

    canditates_by_uris = {}

    for instance_name in play_hosts:
        instance_vars = module_hostvars[instance_name]
        instance_config = instance_vars.get('config')

        if any([
            helpers.is_stateboard(instance_vars),
            not helpers.is_enabled(instance_vars),
            instance_name in cluster_disabled_instances,
            instance_config is None
        ]):
            continue

        advertise_uri = instance_config['advertise_uri']
        canditates_by_uris[advertise_uri] = instance_name

    alive_not_expelled_instance_name = None
    for uri, instance_name in sorted(canditates_by_uris.items()):
        # check defaults for box.cfg parameters
        instance_vars = module_hostvars[instance_name]
        defaults = instance_vars.get('cartridge_defaults')
        if 'transport' in defaults:
            is_ssl = defaults['transport'] == 'ssl'

        # set host:port according to advertise uri
        host, port = uri.rsplit(':', 1)

        try:
            if is_ssl:
                warnings.append("%s: connecting to iproto with SSL" % instance_name)
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.check_hostname = False
                context.load_verify_locations(cafile=defaults['ssl_client_ca_file'])
                context.load_cert_chain(defaults['ssl_client_cert_file'], defaults['ssl_client_key_file'])

                with socket.create_connection((host, port), timeout=CONNECTION_TIMEOUT) as sock:
                    with context.wrap_socket(sock) as ssock:
                        warnings.append("%s: %s" % (instance_name, ssock.version()))
                        ssock.settimeout(CONNECTION_TIMEOUT)
                        ssock.recv(1024)
            else:
                warnings.append("%s: connecting to iproto without SSL" % instance_name)
                conn = socket.create_connection((host, port), timeout=CONNECTION_TIMEOUT)
                conn.settimeout(CONNECTION_TIMEOUT)
                conn.recv(1024)
        except (socket.error, ssl.SSLError) as err:
            warnings.append("%s: error -- %s" % (instance_name, str(err)))
            continue

        alive_not_expelled_instance_name = instance_name
        break

    if alive_not_expelled_instance_name is None:
        errmsg = "Not found any alive instance that is not expelled, not disabled and not a stateboard"
        return helpers.ModuleRes(failed=True, msg=errmsg, warnings=warnings)

    instance_vars = module_hostvars[alive_not_expelled_instance_name]
    run_dir = instance_vars.get('cartridge_run_dir')
    console_sock = helpers.get_instance_console_sock(
        run_dir, app_name, alive_not_expelled_instance_name,
    )

    return helpers.ModuleRes(changed=False, fact={
        'name': alive_not_expelled_instance_name,
        'console_sock': console_sock,
    }, warnings=warnings)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_alive_not_expelled_instance)
