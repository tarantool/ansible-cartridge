#!/usr/bin/python

import os

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console


argument_spec = {
    'control_sock': {'required': True, 'type': 'str'},
}


def check_joined(params):
    joined = False

    if os.path.exists(params['control_sock']):
        control_console = get_control_console(params['control_sock'])
        joined = control_console.eval('''
            local replicasets = require('cartridge').admin_get_replicasets()
            return replicasets ~= nil and #replicasets > 0
        ''')

    return ModuleRes(success=True, changed=False, meta={'joined': joined})


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        res = check_joined(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
