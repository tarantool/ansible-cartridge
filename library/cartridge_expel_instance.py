#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes
from ansible.module_utils.helpers import get_control_console
from ansible.module_utils.helpers import get_all_cluster_instances


argument_spec = {
    'alias': {'required': True, 'type': 'str'},
    'control_sock': {'required': True, 'type': 'str'},
}


def expel_intstance(params):
    control_console = get_control_console(params['control_sock'])
    instance_alias = params['alias']

    # Get instance info
    cluster_instances = get_all_cluster_instances(control_console)

    cluster_instance = None
    for i in cluster_instances:
        if i['alias'] == instance_alias:
            cluster_instance = i
            break

    if cluster_instance is None or cluster_instance.get('uuid') is None:
        return ModuleRes(success=True, changed=False)

    res = control_console.eval('''
        local res, err = require('cartridge').admin_edit_topology({{
            servers = {{
                {{
                    uuid = "{}",
                    expelled = true,
                }}
            }}
        }})
        return {{
            ok = err == nil,
            err = err ~= nil and err.err or box.NULL
        }}
    '''.format(cluster_instance['uuid']))

    if not res['ok']:
        errmsg = 'Failed to expel instance {}: {}'.format(instance_alias, res['err'])
        return ModuleRes(success=False, msg=errmsg)

    return ModuleRes(success=True, changed=True)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = expel_intstance(module.params)

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
