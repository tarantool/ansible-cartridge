import os


def path_join(parts):
    return os.path.join(*parts)


def add_trailing_slash(path):
    if path.endswith(os.path.sep):
        return path

    return path + os.path.sep


def get_cached_facts(hostvars, fact_names_by_target, accum_dict_name='role_facts'):
    cached_facts = {}
    for instance_name, instance_vars in hostvars.items():
        role_vars = instance_vars.get(accum_dict_name, {})

        for target, fact_names in fact_names_by_target.items():
            cached_facts[target] = cached_facts.get(target, {})
            cached_facts[target][instance_name] = cached_facts[target].get(instance_name, {})

            for fact_name in fact_names:
                if fact_name in role_vars:
                    cached_facts[target][instance_name][fact_name] = role_vars[fact_name]
                elif fact_name in instance_vars:
                    cached_facts[target][instance_name][fact_name] = instance_vars[fact_name]

    return cached_facts


class FilterModule(object):
    def filters(self):
        return {
            'cartridge_path_join': path_join,
            'cartridge_add_trailing_slash': add_trailing_slash,
            'get_cached_facts': get_cached_facts,
        }
