#!/usr/bin/env python

import jinja2
import yaml

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'vars': {'required': True, 'type': 'dict'},
    'default_vars': {'required': True, 'type': 'dict'},
}

jinja_env = jinja2.Environment(loader=jinja2.BaseLoader())


def resolve_var_values(all_vars, var_value):
    if isinstance(var_value, list):
        for value in var_value:
            resolve_var_values(all_vars, value)

    elif isinstance(var_value, dict):
        for key, value in var_value.items():
            var_value[key] = resolve_var_values(all_vars, value)

    elif isinstance(var_value, str):
        # For Ansible 2.8
        old_value = None
        new_value = var_value
        while new_value != old_value:
            old_value = new_value
            new_value = jinja_env.from_string(old_value).render(**all_vars)

        var_value = yaml.safe_load(new_value)

    return var_value


def get_cached_facts(params):
    all_vars = params['vars']
    default_vars = params['default_vars']

    role_vars = {}
    for var_name in default_vars:
        role_vars[var_name] = resolve_var_values(all_vars, all_vars[var_name])

    return helpers.ModuleRes(changed=False, facts={
        'role_vars': role_vars,
    })


if __name__ == '__main__':
    helpers.execute_module(argument_spec, get_cached_facts)
