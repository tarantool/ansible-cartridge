#!/usr/bin/python

import re

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes


argument_spec = {
    'hosts': {'required': True, 'type': 'list'},
    'hostvars': {'required': True, 'type': 'dict'}
}

INSTANCE_REQUIRED_PARAMS = ['cartridge_app_name', 'cartridge_cluster_cookie', 'config']
PARAMS_THE_SAME_FOR_ALL_HOSTS = [
    'cartridge_app_name',
    'cartridge_cluster_cookie',
    'cartridge_auth',
    'cartridge_bootstrap_vshard',
    'cartridge_failover',
    'cartridge_allow_downgrade',
    'cartridge_app_config',
]

CONFIG_REQUIRED_PARAMS = ['advertise_uri']
CONFIG_FORBIDDEN_PARAMS = ['alias', 'console_sock', 'pid_file', 'workdir', 'cluster_cookie']

REPLICASET_REQUIRED_PARAMS = ['failover_priority', 'roles']

CLUSTER_COOKIE_MAX_LEN = 256
CLUSTER_COOKIE_FORBIDDEN_SYMBOLS_RGX = r'[^a-zA-Z0-9_.~-]+'


def is_valid_advertise_uri(uri):
    rgx = re.compile(r'^\S+:\d+$')
    return re.match(rgx, uri) is not None


def check_schema(schema, conf, path=''):
    if isinstance(schema, dict):
        if not isinstance(conf, dict):
            return False, '{} must be {}'.format(path, dict)
        for k in schema:
            if k in conf:
                subpath = '{}.{}'.format(path, k)
                ok, err = check_schema(schema[k], conf[k], subpath)
                if not ok:
                    return False, err
        return True, None
    elif isinstance(schema, list):
        if not isinstance(conf, list):
            return False, '{} must be {}'.format(path, list)
        for i, c in enumerate(conf):
            subpath = '{}[{}]'.format(path, i)
            ok, err = check_schema(schema[0], c, subpath)
            if not ok:
                return False, err
        return True, None
    elif isinstance(schema, type):
        if schema in [float, int]:
            if not (isinstance(conf, float) or isinstance(conf, int)):
                return False, '{} must be {}'.format(path, schema)
        else:
            if not isinstance(conf, schema):
                return False, '{} must be {}'.format(path, schema)
        return True, None
    else:
        return False, 'Wrong type'


def validate_types(vars):
    schema = {
        'cartridge_package_path': str,
        'cartridge_app_name': str,
        'cartridge_cluster_cookie': str,
        'cartridge_defaults': dict,
        'cartridge_failover': bool,
        'cartridge_app_config': dict,
        'cartridge_auth': {
            'enabled': bool,
            'cookie_max_age': int,
            'cookie_renew_age': int,
            'users': [
                {
                    'username': str,
                    'password': str,
                    'fullname': str,
                    'email': str,
                    'deleted': bool,
                }
            ]
        },
        'config': {
            'advertise_uri': str,
            'memtx_memory': int,
        },
        'restarted': bool,
        'expelled': bool,
        'instance_start_timeout': int,
        'roles': [str],
        'failover_priority': [str],
        'replicaset_alias': str,
        'vshard_group': str,
    }

    return check_schema(schema, vars)


def check_cluster_cookie_symbols(cluster_cookie):
    if len(cluster_cookie) > CLUSTER_COOKIE_MAX_LEN:
        errmsg = 'Cluster cookie сannot be longer than {}'.format(CLUSTER_COOKIE_MAX_LEN)
        return False, errmsg

    m = re.search(CLUSTER_COOKIE_FORBIDDEN_SYMBOLS_RGX, cluster_cookie)
    if m is not None:
        errmsg = 'Cluster cookie cannot contain symbols other than [a-zA-Z0-9_.~-] ' + \
            '("{}" found)'.format(m.group())
        return False, errmsg

    return True, None


def check_required_params(host_vars, host):
    for p in INSTANCE_REQUIRED_PARAMS:
        if host_vars.get(p) is None:
            errmsg = '"{}" must be specified (misseg for "{}")'.format(p, host)
            return False, errmsg

    return True, None


def check_instance_config(config, host):
    # Check if all required params are specified
    for p in CONFIG_REQUIRED_PARAMS:
        if config.get(p) is None:
            errmsg = 'Missed required parameter "{}" in "{}" config'.format(p, host)
            return False, errmsg

    # Check if no forbidden params specified
    for p in CONFIG_FORBIDDEN_PARAMS:
        if config.get(p) is not None:
            errmsg = 'Specified forbidden parameter "{}" in "{}" config'.format(p, host)
            return False, errmsg

    return True, None


def check_params_the_same_for_all_hosts(host_vars, found_common_params):
    for p in PARAMS_THE_SAME_FOR_ALL_HOSTS:
        if found_common_params.get(p) is not None:
            if host_vars.get(p) != found_common_params.get(p):
                errmsg = '"{}" must be the same for all hosts'.format(p)
                return False, errmsg
        elif host_vars.get(p) is not None:
            found_common_params[p] = host_vars.get(p)

    return True, None


def validate_config(params):
    all_replicasets = {}

    found_common_params = {}

    for host in params['hosts']:
        host_vars = params['hostvars'][host]

        ok, errmsg = validate_types(host_vars)
        if not ok:
            return ModuleRes(success=False, msg=errmsg)

        ok, errmsg = check_required_params(host_vars, host)
        if not ok:
            return ModuleRes(success=False, msg=errmsg)

        ok, errmsg = check_instance_config(host_vars['config'], host)
        if not ok:
            return ModuleRes(success=False, msg=errmsg)

        ok, errmsg = check_params_the_same_for_all_hosts(host_vars, found_common_params)
        if not ok:
            return ModuleRes(success=False, msg=errmsg)

        if 'cartridge_defaults' in host_vars:
            if 'cluster_cookie' in host_vars['cartridge_defaults']:
                errmsg = 'Cluster cookie must be specified in "cartridge_cluster_cookie", not in "cartridge_defaults"'
                return ModuleRes(success=False, msg=errmsg)

        if host_vars.get('expelled') is True and host_vars.get('restarted') is True:
            errmsg = 'Flags "expelled" and "restarted" can not be set at the same time'
            return ModuleRes(success=False, msg=errmsg)

        ok, errmsg = check_cluster_cookie_symbols(host_vars['cartridge_cluster_cookie'])
        if not ok:
            return ModuleRes(success=False, msg=errmsg)

        if 'advertise_uri' in host_vars['config']:
            if not is_valid_advertise_uri(host_vars['config']['advertise_uri']):
                errmsg = 'Instance advertise_uri must be specified as "<host>:<port>" ("{}")'.format(host)
                return ModuleRes(success=False, msg=errmsg)

        # Check replicasets
        if 'replicaset_alias' in host_vars:
            replicaset_alias = host_vars['replicaset_alias']
            if replicaset_alias not in all_replicasets:
                for p in REPLICASET_REQUIRED_PARAMS:
                    if p not in host_vars:
                        errmsg = 'Parameter "{}" is required for all replicasets (missed for "{}")'.format(
                            p, replicaset_alias
                        )
                        return ModuleRes(success=False, msg=errmsg)
                # Save replicaset info
                all_replicasets[replicaset_alias] = {
                    'roles': host_vars['roles'] if 'roles' in host_vars else None,
                    'failover_priority': host_vars['failover_priority'] if 'failover_priority' in host_vars else None,
                    'vshard_group': host_vars['vshard_group'] if 'vshard_group' in host_vars else None,
                }
            else:
                replicaset = {
                    'roles': host_vars['roles'] if 'roles' in host_vars else None,
                    'failover_priority': host_vars['failover_priority'] if 'failover_priority' in host_vars else None,
                    'vshard_group': host_vars['vshard_group'] if 'vshard_group' in host_vars else None,
                }
                if replicaset != all_replicasets[replicaset_alias]:
                    errmsg = 'Replicaset parameters must be the same for all instances' + \
                        ' with the same "replicaset_alias" ("{}")'.format(replicaset_alias)
                    return ModuleRes(success=False, msg=errmsg)

    # Check cartridge_auth
    cartridge_auth = found_common_params.get('cartridge_auth')
    if cartridge_auth is not None:
        if 'users' in cartridge_auth:
            for user in cartridge_auth['users']:
                if 'username' not in user:
                    errmsg = 'Field "username" is required for "cartridge_auth.users"'
                    return ModuleRes(success=False, msg=errmsg)

    # Check app_config
    app_config = found_common_params.get('cartridge_app_config')
    if app_config is not None:
        for section_name, section in app_config.items():
            if not isinstance(section, dict):
                errmsg = '"cartridge_app_config.{}" must be dict, found {}'.format(
                    section_name, type(section)
                )
                return ModuleRes(success=False, msg=errmsg)

            if not section:
                errmsg = '"cartridge_app_config.{}" must have "body" or "deleted" subsection'.format(section_name)
                return ModuleRes(success=False, msg=errmsg)

            allowed_keys = ['body', 'deleted']
            for key in section:
                if key not in allowed_keys:
                    errmsg = '"cartridge_app_config.{}" can contain only "body" or "deleted" subsections'.format(
                        section_name
                    )
                    return ModuleRes(success=False, msg=errmsg)

            if 'deleted' in section:
                if not isinstance(section['deleted'], bool):
                    errmsg = '"cartridge_app_config.{}.deleted" must be bool, found {}'.format(
                        section_name, type(section['deleted'])
                    )
                    return ModuleRes(success=False, msg=errmsg)

                if section['deleted'] is False:
                    if 'body' not in section:
                        errmsg = '"cartridge_app_config.{}.body" is required'.format(section_name)
                        return ModuleRes(success=False, msg=errmsg)

    return ModuleRes(success=True, changed=False)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = validate_config(module.params)

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
