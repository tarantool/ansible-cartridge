#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule

from ansible.module_utils.helpers import ModuleRes
from ansible.module_utils.helpers import is_expelled


argument_spec = {
    'hostvars': {'required': True, 'type': 'dict'},
    'play_hosts': {'required': True, 'type': 'list'},
}


def get_machine_hostname(instance_vars, instance_name):
    if 'ansible_host' in instance_vars:
        return instance_vars['ansible_host']

    raise Exception('Instance %s has not "ansible_host" option!' % instance_name)


def get_one_not_expelled_instance_for_machine(params):
    hostvars = params['hostvars']
    play_hosts = params['play_hosts']

    machine_hostnames = set()
    instance_names = []

    for instance_name in play_hosts:
        instance_vars = hostvars[instance_name]

        if is_expelled(instance_vars):
            continue

        machine_hostname = get_machine_hostname(instance_vars, instance_name)
        if machine_hostname not in machine_hostnames:
            machine_hostnames.add(machine_hostname)
            instance_names.append(instance_name)

    return ModuleRes(success=True, meta={
        'names': instance_names,
    })


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = get_one_not_expelled_instance_for_machine(module.params)
    except Exception as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, **res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
