#!/usr/bin/python

import os

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console


argument_spec = {
    'control_sock': {'required': True, 'type': 'str'},
}


def get_cluster_replicasets(control_console):
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

    return replicasets


def get_current_topology(params):
    replicasets = []
    if os.path.exists(params['control_sock']):
        control_console = get_control_console(params['control_sock'])
        replicasets = get_cluster_replicasets(control_console)
    return ModuleRes(success=True, changed=False, meta={'replicasets': replicasets})


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = get_current_topology(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
