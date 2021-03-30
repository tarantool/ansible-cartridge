#!/usr/bin/python

from ansible.module_utils.helpers import execute_module, ModuleRes
from ansible.module_utils.helpers import get_control_console

argument_spec = {
    'app_config': {'required': True, 'type': 'dict'},
    'console_sock': {'required': True, 'type': 'str'},
}


def section_is_deleted(section):
    return 'deleted' in section and section['deleted'] is True


def config_app(params):
    control_console = get_control_console(params['console_sock'])
    config = params['app_config']

    system_sections = {
        'topology': True,
        'vshard': True,
        'vshard_groups': True,
        'auth': True,
        'users_acl': True,
    }

    # Get current config
    current_config, _ = control_console.eval_res_err('''
        local config = require('cartridge').config_get_readonly()
        return config
    ''')

    if config is None:
        return ModuleRes(failed=True, msg="Cluster isn't bootstrapped yet")

    # Patch it
    patch = {}
    changed = False

    for section_name, section in config.items():
        if section_name in system_sections:
            errmsg = 'Unable to patch config system section: "{}"'.format(section_name)
            return ModuleRes(failed=True, msg=errmsg)

        if section_is_deleted(section):
            if section_name in current_config:
                patch[section_name] = None
                changed = True
        else:
            if section_name not in current_config or current_config[section_name] != section['body']:
                patch[section_name] = section['body']
                changed = True

    if not changed:
        return ModuleRes(changed=False)

    func_body = '''
        local patch = ...
        return require('cartridge').config_patch_clusterwide(patch)
    '''
    ok, err = control_console.eval_res_err(func_body, patch)

    if not ok:
        errmsg = 'Config patch failed: {}'.format(err)
        return ModuleRes(failed=True, msg=errmsg)

    return ModuleRes()


if __name__ == '__main__':
    execute_module(argument_spec, config_app)
