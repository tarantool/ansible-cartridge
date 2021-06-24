#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
}


def check_state(params):
    if helpers.is_instance_started(params['console_sock']):
        return helpers.ModuleRes(failed=True, msg="instance shouldn't be running")

    return helpers.ModuleRes(changed=False)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, check_state)
