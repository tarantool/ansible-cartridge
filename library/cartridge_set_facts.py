#!/usr/bin/python

import pkgutil

if pkgutil.find_loader('ansible.module_utils.helpers'):
    import ansible.module_utils.helpers as helpers
else:
    import module_utils.helpers as helpers

argument_spec = {
    'facts': {'required': True, 'type': 'dict'},
}


def set_facts(params):
    return helpers.ModuleRes(changed=False, facts=params['facts'])


if __name__ == '__main__':
    helpers.execute_module(argument_spec, set_facts)
