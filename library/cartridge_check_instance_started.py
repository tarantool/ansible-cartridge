#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console


argument_spec = {
    'control_sock': {'required': True, 'type': 'str'},
    'stateboard': {'required': True, 'type': 'bool'},
}


def check_instance_started(params):
    try:
        control_console = get_control_console(params['control_sock'])
        instance_is_alive = True
        if not params['stateboard']:
            instance_is_alive, _ = control_console.eval_res_err('''
                return require('membership').myself().status == 'alive'
            ''')
    except CartridgeException as e:
        return ModuleRes(success=False, msg=str(e))

    return ModuleRes(success=instance_is_alive)


def main():
    module = AnsibleModule(argument_spec=argument_spec)

    try:
        res = check_instance_started(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
