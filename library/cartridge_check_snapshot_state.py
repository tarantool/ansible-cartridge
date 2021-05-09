#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
}


def check_snapshot_state(control_console):
    snapshot, err = control_console.eval_res_err('''
        return box.info().gc().checkpoint_is_in_progress
    ''')
    if err:
        return helpers.ModuleRes(failed=True, msg="Impossible to get snapshot state: %s" % err)

    if snapshot:
        return helpers.ModuleRes(failed=True, msg="Snapshot is still in progress")

    return helpers.ModuleRes(changed=False)


def check_state(params):
    try:
        control_console = helpers.get_control_console(params['console_sock'])
        return check_snapshot_state(control_console)

    except helpers.CartridgeException as e:
        return helpers.ModuleRes(exception=e)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, check_state)
