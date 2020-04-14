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
    'cartridge_app_config',
]

CONFIG_REQUIRED_PARAMS = ['advertise_uri']
CONFIG_FORBIDDEN_PARAMS = ['alias', 'console_sock', 'pid_file', 'workdir', 'cluster_cookie']

REPLICASET_PARAMS = [
    'replicaset_alias',
    'failover_priority',
    'roles',
    'all_rw',
    'weight',
    'vshard_group',
]
REPLICASET_REQUIRED_PARAMS = ['roles']

CLUSTER_COOKIE_MAX_LEN = 256
CLUSTER_COOKIE_FORBIDDEN_SYMBOLS_RGX = r'[^a-zA-Z0-9_.~-]+'


def is_valid_advertise_uri(uri):
    rgx = re.compile(r'^\S+:\d+$')
    return re.match(rgx, uri) is not None


def check_schema(schema, conf, path=''):
    if isinstance(schema, dict):
        if not isinstance(conf, dict):
            return '{} must be {}'.format(path, dict)
        for k in schema:
            if k in conf:
                subpath = '{}.{}'.format(path, k)
                errmsg = check_schema(schema[k], conf[k], subpath)
                if errmsg is not None:
                    return errmsg
        return None
    elif isinstance(schema, list):
        if not isinstance(conf, list):
            return '{} must be {}'.format(path, list)
        for i, c in enumerate(conf):
            subpath = '{}[{}]'.format(path, i)
            errmsg = check_schema(schema[0], c, subpath)
            if errmsg is not None:
                return errmsg
        return None
    elif isinstance(schema, type):
        if schema in [float, int]:
            if not (isinstance(conf, float) or isinstance(conf, int)):
                return '{} must be {}'.format(path, schema)
        else:
            if not isinstance(conf, schema):
                return '{} must be {}'.format(path, schema)
        return None
    else:
        return 'Wrong type'


def validate_types(vars):
    schema = {
        'cartridge_package_path': str,
        'cartridge_app_name': str,
        'cartridge_cluster_cookie': str,
        'cartridge_defaults': dict,
        'cartridge_bootstrap_vshard': bool,
        'cartridge_failover': bool,
        'cartridge_app_config': dict,
        'restarted': bool,
        'expelled': bool,
        'instance_start_timeout': int,
        'replicaset_alias': str,
        'failover_priority': [str],
        'roles': [str],
        'all_rw': bool,
        'weight': int,
        'vshard_group': str,
        'cartridge_enable_tarantool_repo': bool,
        'config': {
            'advertise_uri': str,
            'memtx_memory': int,
        },
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
    }

    return check_schema(schema, vars)


def check_cluster_cookie_symbols(cluster_cookie):
    if len(cluster_cookie) > CLUSTER_COOKIE_MAX_LEN:
        errmsg = 'Cluster cookie сannot be longer than {}'.format(CLUSTER_COOKIE_MAX_LEN)
        return errmsg

    m = re.search(CLUSTER_COOKIE_FORBIDDEN_SYMBOLS_RGX, cluster_cookie)
    if m is not None:
        errmsg = 'Cluster cookie cannot contain symbols other than [a-zA-Z0-9_.~-] ' + \
            '("{}" found)'.format(m.group())
        return errmsg

    return None


def check_required_params(host_vars, host):
    for p in INSTANCE_REQUIRED_PARAMS:
        if host_vars.get(p) is None:
            errmsg = '"{}" must be specified (misseg for "{}")'.format(p, host)
            return errmsg

    errmsg = check_cluster_cookie_symbols(host_vars['cartridge_cluster_cookie'])
    if errmsg is not None:
        return errmsg

    return None


def check_instance_config(config, host):
    # Check if all required params are specified
    for p in CONFIG_REQUIRED_PARAMS:
        if config.get(p) is None:
            errmsg = 'Missed required parameter "{}" in "{}" config'.format(p, host)
            return errmsg

    # Check if no forbidden params specified
    for p in CONFIG_FORBIDDEN_PARAMS:
        if config.get(p) is not None:
            errmsg = 'Specified forbidden parameter "{}" in "{}" config'.format(p, host)
            return errmsg

    if 'advertise_uri' in config:
        if not is_valid_advertise_uri(config['advertise_uri']):
            errmsg = 'Instance advertise_uri must be specified as "<host>:<port>" ("{}")'.format(host)
            return errmsg

    return None


def check_params_the_same_for_all_hosts(host_vars, found_common_params):
    for p in PARAMS_THE_SAME_FOR_ALL_HOSTS:
        if found_common_params.get(p) is not None:
            if host_vars.get(p) != found_common_params.get(p):
                errmsg = '"{}" must be the same for all hosts'.format(p)
                return errmsg
        elif host_vars.get(p) is not None:
            found_common_params[p] = host_vars.get(p)

    return None


def check_replicaset(host_vars, found_replicasets):
    if 'replicaset_alias' not in host_vars:
        return None

    replicaset_alias = host_vars['replicaset_alias']

    replicaset = {p: host_vars.get(p) for p in REPLICASET_PARAMS}

    if replicaset_alias not in found_replicasets:
        for p in REPLICASET_REQUIRED_PARAMS:
            if p not in host_vars:
                errmsg = 'Parameter "{}" is required for all replicasets (missed for "{}")'.format(
                    p, replicaset_alias
                )
                return errmsg
        # Save replicaset info
        found_replicasets[replicaset_alias] = replicaset
    else:
        if replicaset != found_replicasets[replicaset_alias]:
            errmsg = 'Replicaset parameters must be the same for all instances' + \
                ' from one replicaset ("{}")'.format(replicaset_alias)
            return errmsg

    return None


def check_app_config(found_common_params):
    app_config = found_common_params.get('cartridge_app_config')
    if app_config is None:
        return None

    for section_name, section in app_config.items():
        if not isinstance(section, dict):
            errmsg = '"cartridge_app_config.{}" must be dict, found {}'.format(
                section_name, type(section)
            )
            return errmsg

        if not section:
            errmsg = '"cartridge_app_config.{}" must have "body" or "deleted" subsection'.format(section_name)
            return errmsg

        allowed_keys = ['body', 'deleted']
        for key in section:
            if key not in allowed_keys:
                errmsg = '"cartridge_app_config.{}" can contain only "body" or "deleted" subsections'.format(
                    section_name
                )
                return errmsg

        if 'deleted' in section:
            if not isinstance(section['deleted'], bool):
                errmsg = '"cartridge_app_config.{}.deleted" must be bool, found {}'.format(
                    section_name, type(section['deleted'])
                )
                return errmsg

            if section['deleted'] is False:
                if 'body' not in section:
                    errmsg = '"cartridge_app_config.{}.body" is required'.format(section_name)
                    return errmsg

    return None


def check_auth(found_common_params):
    cartridge_auth = found_common_params.get('cartridge_auth')
    if cartridge_auth is None:
        return None

    if cartridge_auth is not None:
        if 'users' in cartridge_auth:
            for user in cartridge_auth['users']:
                if 'username' not in user:
                    errmsg = 'Field "username" is required for "cartridge_auth.users"'
                    return errmsg

    return None


def validate_config(params):
    found_replicasets = {}
    found_common_params = {}

    for host in params['hosts']:
        host_vars = params['hostvars'][host]

        # Validate types
        errmsg = validate_types(host_vars)
        if errmsg is not None:
            return ModuleRes(success=False, msg=errmsg)

        # All required params should be specified
        errmsg = check_required_params(host_vars, host)
        if errmsg is not None:
            return ModuleRes(success=False, msg=errmsg)

        # Instance config
        errmsg = check_instance_config(host_vars['config'], host)
        if errmsg is not None:
            return ModuleRes(success=False, msg=errmsg)

        # Params common for all instances
        errmsg = check_params_the_same_for_all_hosts(host_vars, found_common_params)
        if errmsg is not None:
            return ModuleRes(success=False, msg=errmsg)

        # Cartridge defaults
        if 'cartridge_defaults' in host_vars:
            if 'cluster_cookie' in host_vars['cartridge_defaults']:
                errmsg = 'Cluster cookie must be specified in "cartridge_cluster_cookie", not in "cartridge_defaults"'
                return ModuleRes(success=False, msg=errmsg)

        # Instance state
        if host_vars.get('expelled') is True and host_vars.get('restarted') is True:
            errmsg = 'Flags "expelled" and "restarted" can not be set at the same time'
            return ModuleRes(success=False, msg=errmsg)

        # Replicasets
        errmsg = check_replicaset(host_vars, found_replicasets)
        if errmsg is not None:
            return ModuleRes(success=False, msg=errmsg)

    # Authorization params
    errmsg = check_auth(found_common_params)
    if errmsg is not None:
        return ModuleRes(success=False, msg=errmsg)

    # Clusterwide config
    errmsg = check_app_config(found_common_params)
    if errmsg is not None:
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
