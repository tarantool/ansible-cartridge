#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'app_config': {'required': True, 'type': 'dict'},
    'console_sock': {'required': True, 'type': 'str'},
    'netbox_call_timeout': {'required': False, 'type': 'int'},
    'upload_config_timeout': {'required': False, 'type': 'int'},
    'apply_config_timeout': {'required': False, 'type': 'int'},
    'validate_config_timeout': {'required': False, 'type': 'int'},
}


def section_is_deleted(section):
    return 'deleted' in section and section['deleted'] is True


def config_app(params):
    control_console = helpers.get_control_console(params['console_sock'])
    config = params['app_config']

    new_sections = {}
    for section_name, section in config.items():
        if section_is_deleted(section):
            new_sections[section_name] = None
        else:
            new_sections[section_name] = section.get('body')

    helpers.set_twophase_options_from_params(control_console, params)

    changed, err = helpers.patch_clusterwide_config(control_console, new_sections)
    if err is not None:
        return helpers.ModuleRes(failed=True, msg=err)

    return helpers.ModuleRes(changed=changed)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, config_app)
