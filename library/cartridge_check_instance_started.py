#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console


argument_spec = {
    'control_sock': {'required': True, 'type': 'str'},
    'stateboard': {'required': True, 'type': 'bool'},
    'waiting_for_state': {'required': False, 'type': 'list', 'default': ['Unconfigured', 'RolesConfigured']},
}


def check_instance_started(params):
    waiting_for_state = params['waiting_for_state']
    try:
        control_console = get_control_console(params['control_sock'])
        ok = True
        if not params['stateboard']:
            ok = control_console.eval('''
                return require('membership').myself().status == 'alive'
            ''')
            if ok is True:
                response = control_console.eval('''
                    local state, err = require('cartridge.confapplier').get_state()
                    return {
                        state = state,
                        err = err or box.NULL
                    }
                ''')
                state = response['state']
                err = response['err']
                if state in waiting_for_state:
                    return ModuleRes(success=ok)
                else:
                    return ModuleRes(success=False, msg=('Instance state is {}. Error: {}').format(state, err))
    except CartridgeException as e:
        return ModuleRes(success=False, msg=str(e))

    if not params['stateboard']:
        return ModuleRes(success=False, msg='Instance is not running')
    else:
        return ModuleRes(success=True, msg='This is a stateboard instance')


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
