#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'body': {'required': True, 'type': 'str'},
    'args': {'required': False, 'default': [], 'type': 'list'},
}


def eval_code(params):
    body = params['body']
    args = params['args']

    control_console = helpers.get_control_console(params['console_sock'])
    eval_res = control_console.eval(body, *args)

    return helpers.ModuleRes(changed=False, fact=eval_res)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, eval_code)
