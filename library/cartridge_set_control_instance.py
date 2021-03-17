#!/usr/bin/python

import pkgutil

if pkgutil.find_loader('ansible.module_utils.helpers'):
    import ansible.module_utils.helpers as helpers
else:
    import module_utils.helpers as helpers

argument_spec = {
    'hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
    'console_sock': {'required': True, 'type': 'str'},
    'app_name': {'required': True, 'type': 'str'},
}


def get_control_instance(params):
    hostvars = params['hostvars']
    play_hosts = params['play_hosts']
    console_sock = params['console_sock']
    app_name = params['app_name']

    control_console = helpers.get_control_console(console_sock)
    control_instance_name = None

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
            if instance_name not in hostvars:
                continue

            control_instance_name = instance_name
            break

    if control_instance_name is None:
        for instance_name in play_hosts:
            instance_vars = hostvars[instance_name]
            if helpers.is_expelled(instance_vars) or helpers.is_stateboard(instance_vars):
                continue

            if 'replicaset_alias' in instance_vars:
                control_instance_name = instance_name
                break

    if control_instance_name is None:
        errmsg = 'Not found any joined instance or instance to create a replicaset'
        return helpers.ModuleRes(failed=True, msg=errmsg)

    # in the ideal imagined world we could just use
    # instance_vars['instance_info'], but if control instance is not
    # in play_hosts, instance_info isn't computed for it
    instance_vars = hostvars[control_instance_name]
    run_dir = instance_vars.get('cartridge_run_dir', helpers.DEFAULT_RUN_DIR)
    control_instance_console_sock = helpers.get_instance_console_sock(
        run_dir, app_name, control_instance_name,
    )

    return helpers.ModuleRes(changed=False, facts={
        'control_instance': {
            'name': control_instance_name,
            'console_sock': control_instance_console_sock,
        }
    })


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_control_instance)
