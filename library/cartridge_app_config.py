#!/usr/bin/python

import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes
from ansible.module_utils.helpers import get_control_console


argument_spec = {
    'app_config': {'required': True, 'type': 'dict'},
    'control_sock': {'required': True, 'type': 'str'},
}


def section_is_deleted(section):
    return 'deleted' in section and section['deleted'] is True


def config_app(params):
    control_console = get_control_console(params['control_sock'])
    config = params['app_config']

    system_sections = {
        'topology': True,
        'vshard': True,
        'vshard_groups': True,
        'auth': True,
        'users_acl': True,
    }

    # Get current config
    res = control_console.eval('''
        local cartridge = require('cartridge')
        local config = cartridge.config_get_readonly()
        return {
            ok = config ~= nil,
            config = config ~= nil and config or "Cluster isn't bootstrapped yet",
        }
    ''')
    if not res['ok']:
        errmsg = 'Config upload failed: {}'.format(res['config'])
        return ModuleRes(success=False, msg=errmsg)

    current_config = res['config']

    # Patch it
    patch = {}
    changed = False

    for section_name, section in config.items():
        if section_name in system_sections:
            return ModuleRes('Unable to patch config system section: "{}"'.format(section_name))

        if section_is_deleted(section):
            if section_name in current_config:
                patch[section_name] = None
                changed = True
        else:
            if section_name not in current_config or current_config[section_name] != section['body']:
                patch[section_name] = section['body']
                changed = True

    if not changed:
        return ModuleRes(success=True, changed=False)

    res = control_console.eval('''
        local cartridge = require('cartridge')
        local patch = require('json').decode('{}')
        local ok, err = cartridge.config_patch_clusterwide(patch)
        return {{
            ok = ok == true,
            err = err and err.err or require('json').NULL
        }}
    '''.format(json.dumps(patch)))

    if not res['ok']:
        errmsg = 'Config upload failed: {}'.format(res['err'])
        return ModuleRes(success=False, msg=errmsg)

    return ModuleRes(success=True, changed=True)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = config_app(module.params)

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
