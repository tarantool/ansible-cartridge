#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
}


def check_cluster_state(control_console):
    issues, err = control_console.eval_res_err('''
        if not require("cartridge.topology").cluster_is_healthy() then
            return 1e5
        end
        return #require("cartridge.issues").list_on_cluster()
    ''')
    if err:
        return helpers.ModuleRes(failed=True, msg="Impossible to get cluster state: %s" % err)

    if issues == 1e5:
        return helpers.ModuleRes(failed=True, msg="Cluster is not healthy")

    if issues != 0:
        return helpers.ModuleRes(failed=True, msg="Cluster runs %d issues" % int(issues))

    return helpers.ModuleRes(changed=False)


def check_state(params):
    try:
        control_console = helpers.get_control_console(params['console_sock'])
        return check_cluster_state(control_console)

    except helpers.CartridgeException as e:
        return helpers.ModuleRes(exception=e)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, check_state)
