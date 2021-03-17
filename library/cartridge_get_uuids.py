#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console
from ansible.module_utils.helpers import is_expelled, is_stateboard, is_healthy


argument_spec = {
    'control_sock': {'required': True, 'type': 'str'},
    'instances': {'required': True, 'type': 'list'},
    'replicasets': {'required': True, 'type': 'list'},
    'hostvars': {'required': True, 'type': 'dict'},
}


def get_uuids(control_console, instances_to_find, replicasets, hostvars):
    res = []
    found_replicasets = []

    for instance_name in sorted(instances_to_find):
        if is_expelled(hostvars[instance_name]) or is_stateboard(hostvars[instance_name]):
            continue
        response = control_console.eval('''
            local membership = require('membership')
            local member = membership.get_member('{}')
            if member == nil or member.status ~= 'alive' or member.payload.state ~= 'RolesConfigured' then
                return box.NULL
            end
            local replicasets = require('cartridge').admin_get_replicasets()
            for _, r in ipairs(replicasets) do
                for _, s in ipairs(r.servers) do
                    if s.alias == '{}' then
                        return {{
                            replicaset_uuid = r.uuid,
                            instance_uuid = s.uuid
                        }}
                    end
                end
            end
            return box.NULL
        '''.format(hostvars[instance_name]['config']['advertise_uri'], instance_name))

        if response is None:
            continue

        if response['replicaset_uuid'] not in found_replicasets:
            found_replicasets.append(response['replicaset_uuid'])
            res.append(response)

    return ModuleRes(success=True, changed=False, meta=res)


def manage_get_uuids(params):
    instance_names = params.get('instances')
    replicasets = params.get('replicasets')
    control_console = get_control_console(params['control_sock'])
    hostvars = params['hostvars']
    return get_uuids(control_console, instance_names, replicasets, hostvars)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = manage_get_uuids(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
