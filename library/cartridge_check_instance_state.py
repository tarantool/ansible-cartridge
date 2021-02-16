#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes, CartridgeException
from ansible.module_utils.helpers import get_control_console

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'stateboard': {'required': True, 'type': 'bool'},
    'expected_states': {'required': False, 'type': 'list', 'default': ['Unconfigured', 'RolesConfigured']},
    'check_buckets_are_discovered': {'required': False, 'type': 'bool', 'default': True},
}


def check_stateboard_state(control_console):
    box_status, err = control_console.eval_res_err('''
        if type(box.cfg) == 'function' or box.cfg.listen == nil then
            return nil, "box hasn't been configured"
        end
        return true
    ''')
    if not box_status:
        return ModuleRes(success=False, msg="Stateboard is not running: %s" % err)

    return ModuleRes(success=True)


def check_instance_state(control_console, expected_states, check_buckets_are_discovered):
    instance_state, err = control_console.eval_res_err('''
        return require('cartridge.confapplier').get_state()
    ''')
    if not instance_state:
        return ModuleRes(success=False, msg="Impossible to get state: %s" % err)
    if instance_state not in expected_states:
        return ModuleRes(
            success=False,
            msg="Instance is not in one of states: %s, it's in '%s' state" % (
                expected_states,
                instance_state,
            ),
        )

    if check_buckets_are_discovered:
        buckets_ok, err = control_console.eval_res_err('''
            local vshard_utils = require('cartridge.vshard-utils')
            local vshard_router = require('cartridge.roles.vshard-router')

            local function check_group_buckets(group_name, group_opts)
                if not group_opts.bootstrapped then
                    return true
                end

                local router = vshard_router.get(group_name)
                if router == nil then
                    return true
                end

                local unknown_buckets = router:info().bucket.unknown
                if unknown_buckets == 0 then
                    return true
                end

                return nil, string.format(
                    "%s out of %s buckets are not discovered in group '%s'",
                    unknown_buckets,
                    group_opts.bucket_count,
                    group_name
                )
            end

            local groups = vshard_utils.get_known_groups()
            for group_name, group_opts in pairs(groups) do
                local _, err = check_group_buckets(group_name, group_opts)
                if err ~= nil then
                    return nil, err
                end
            end

            return true
        ''')
        if not buckets_ok:
            return ModuleRes(success=False, msg=err)

    return ModuleRes(success=True)


def check_state(params):
    try:
        control_console = get_control_console(params['console_sock'])

        if params['stateboard']:
            return check_stateboard_state(control_console)
        else:
            return check_instance_state(
                control_console,
                params['expected_states'],
                params['check_buckets_are_discovered'],
            )

    except CartridgeException as e:
        return ModuleRes(success=False, msg=str(e))


def main():
    module = AnsibleModule(argument_spec=argument_spec)

    try:
        res = check_state(module.params)
    except CartridgeException as e:
        module.fail_json(msg=str(e))

    if res.success is True:
        module.exit_json(changed=res.changed, **res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
