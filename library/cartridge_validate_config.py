#!/usr/bin/python

import re

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes


argument_spec = {
    'hosts': {'required': True, 'type': 'list'},
    'hostvars': {'required': True, 'type': 'dict'}
}

INSTANCE_REQUIRED_PARAMS = ['name', 'advertise_uri']
INSTANCE_FORBIDDEN_PARAMS = ['alias']
REPLICASET_REQUIRED_PARAMS = ['name', 'instances', 'roles']


def is_valid_advertise_uri(uri):
    rgx = re.compile(r'\S+:\d+')
    return re.match(rgx, uri) is not None


def check_schema(schema, conf, path=''):
    if isinstance(schema, dict):
        for k in schema:
            if k in conf:
                subpath = '{}.{}'.format(path, k)
                ok, err = check_schema(schema[k], conf[k], subpath)
                if not ok:
                    return False, err
        return True, None
    elif isinstance(schema, list):
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
        'cartridge_instances': [
            {
                'name': str,
                'advertise_uri': str,
                'http_port': str,
            }
        ],
        'cartridge_replicasets': [
            {
                'name': str,
                'roles': [str],
                'instances': [str],
                'weight': float,
                'all_rw': bool,
            }
        ],
        'cartridge_app_config': dict
    }

    return check_schema(schema, vars)


def validate_config(params):
    all_instances = {}
    all_replicasets = {}

    # To check if this params are equal for all hosts
    app_name = None
    cluster_cookie = None
    cartridge_auth = None
    app_config = None

    for host in params['hosts']:
        host_vars = params['hostvars'][host]

        ok, errmsg = validate_types(host_vars)
        if not ok:
            return ModuleRes(success=False, msg=errmsg)

        # Check if at least one of app_name and package_path specified
        if 'cartridge_app_name' not in host_vars and 'cartridge_package_path' not in host_vars:
            errmsg = 'At least one of `cartridge_app_name` and `cartridge_package_path` must be specified'
            return ModuleRes(success=False, msg=errmsg)

        # Check app_name
        if app_name is not None:
            if 'cartridge_app_name' in host_vars and host_vars['cartridge_app_name'] != app_name:
                errmsg = '`cartridge_app_name` name must be the same for all hosts'
                return ModuleRes(success=False, msg=errmsg)
        elif 'cartridge_app_name' in host_vars:
            app_name = host_vars['cartridge_app_name']

        # Check cluster auth
        if cartridge_auth is not None:
            if 'cartridge_auth' in host_vars and host_vars['cartridge_auth'] != cartridge_auth:
                errmsg = '`cartridge_auth` name must be the same for all hosts'
                return ModuleRes(success=False, msg=errmsg)
        elif 'cartridge_auth' in host_vars:
            cartridge_auth = host_vars['cartridge_auth']

        # Check app config
        if app_config is not None:
            if 'cartridge_app_config' in host_vars and host_vars['cartridge_app_config'] != app_config:
                errmsg = '`cartridge_app_config` name must be the same for all hosts'
                return ModuleRes(success=False, msg=errmsg)
        elif 'cartridge_app_config' in host_vars:
            app_config = host_vars['cartridge_app_config']

        if 'cartridge_instances' in host_vars:
            # Check cluster cookie
            if 'cartridge_cluster_cookie' not in host_vars:
                errmsg = '`cartridge_cluster_cookie` must be specified'
                return ModuleRes(success=False, msg=errmsg)

            # Check if cookie is the same for all hosts
            if cluster_cookie is not None:
                if host_vars['cartridge_cluster_cookie'] != cluster_cookie:
                    errmsg = 'Cluster cookie must be the same for all hosts'
                    return ModuleRes(success=False, msg=errmsg)
            else:
                cluster_cookie = host_vars['cartridge_cluster_cookie']

        if 'cartridge_defaults' in host_vars:
            if 'cluster_cookie' in host_vars['cartridge_defaults']:
                errmsg = 'Cluster cookie must be specified in `cartridge_cluster_cookie`, not in `cartridge_defaults`'
                return ModuleRes(success=False, msg=errmsg)

        # Check instances
        if 'cartridge_instances' in host_vars:
            for instance in host_vars['cartridge_instances']:
                # Check if instance name is unique
                if instance['name'] in all_instances:
                    errmsg = 'Duplicate instance name: "{}"'.format(instance['name'])
                    return ModuleRes(success=False, msg=errmsg)

                # Check if all required params are specified
                for p in INSTANCE_REQUIRED_PARAMS:
                    if p not in instance:
                        errmsg = 'Parameter "{}" is required for all instances in `cartridge_instances`'.format(p)
                        return ModuleRes(success=False, msg=errmsg)

                # Check if no forbidden params specified
                for p in INSTANCE_FORBIDDEN_PARAMS:
                    if p in instance:
                        errmsg = 'Parameter "{}" is forbidden for instance config'.format(p)
                        return ModuleRes(success=False, msg=errmsg)

                # Check if cluster_cookie is not specified
                if 'cluster_cookie' in instance:
                    errmsg = '`cluster_cookie is specified for instance "{}"`.'.format(instance['name']) + \
                        'It must be specified ONLY in `cartridge_cluster_cookie` variable.'
                    return ModuleRes(success=False, msg=errmsg)

                if 'advertise_uri' in instance:
                    if not is_valid_advertise_uri(instance['advertise_uri']):
                        errmsg = 'Instance advertise_uri must be specified as `<host>:<port>` ("{}")'.format(
                            instance['name']
                        )
                        return ModuleRes(success=False, msg=errmsg)

                # Save instance info
                all_instances[instance['name']] = instance

        # Check replicasets
        if 'cartridge_replicasets' in host_vars:
            for replicaset in host_vars['cartridge_replicasets']:
                # Check if all required params are specified
                for p in REPLICASET_REQUIRED_PARAMS:
                    if p not in replicaset:
                        errmsg = 'Parameter "{}" is required for all replicasets in `cartridge_replicasets`'.format(p)
                        return ModuleRes(success=False, msg=errmsg)

                # Check if replicaset name is unique
                if replicaset['name'] in all_replicasets:
                    if all_replicasets[replicaset['name']] != replicaset:
                        errmsg = 'Duplicate replicaset name: "{}"'.format(replicaset['name'])
                        return ModuleRes(success=False, msg=errmsg)

                if 'leader' not in replicaset:
                    if len(replicaset['instances']) > 1:
                        errmsg = 'Leader must be specified for replicaset with more than one instance ("{}")'.format(
                            replicaset['name']
                        )

                        return ModuleRes(success=False, msg=errmsg)

                # Save replicaset info
                all_replicasets[replicaset['name']] = replicaset

    # Check if all replicasets instances are described in `cartridge_instances`
    #  and one instance belongs to only one replicaset
    for rname, replicaset in all_replicasets.items():
        for replicaset_instance in replicaset['instances']:
            if replicaset_instance not in all_instances:
                errmsg = 'Replicaset "{}" contains instance "{}" not described in `cartridge_instances`'.format(
                    rname, replicaset_instance
                )
                return ModuleRes(success=False, msg=errmsg)

            if 'belongs_to' not in all_instances[replicaset_instance]:
                all_instances[replicaset_instance]['belongs_to'] = rname
            else:
                errmsg = 'Instance "{}" is configured to belong to "{}" and "{}" replicasets.'.format(
                    replicaset_instance, rname, all_instances[replicaset_instance]['belongs_to']
                )
                return ModuleRes(success=False, msg=errmsg)

    # Check cartridge_auth
    if cartridge_auth is not None:
        if 'users' in cartridge_auth:
            for user in cartridge_auth['users']:
                if 'username' not in user:
                    errmsg = 'Field "username" is required for `cartridge_auth.users`'
                    return ModuleRes(success=False, msg=errmsg)

    # Check app_config
    if app_config is not None:
        for section_name, section in app_config.items():
            if not isinstance(section, dict):
                errmsg = '`cartridge_app_config.{}` must be dict, found {}'.format(
                    section_name, type(section)
                )
                return ModuleRes(success=False, msg=errmsg)

            if not section:
                errmsg = '`cartridge_app_config.{}` must have `body` or `deleted` subsection'.format(section_name)
                return ModuleRes(success=False, msg=errmsg)

            allowed_keys = ['body', 'deleted']
            for key in section:
                if key not in allowed_keys:
                    errmsg = '`cartridge_app_config.{}` can contain only `body` or `deleted` subsections'.format(
                        section_name
                    )
                    return ModuleRes(success=False, msg=errmsg)

            if 'deleted' in section:
                if not isinstance(section['deleted'], bool):
                    errmsg = '`cartridge_app_config.{}.deleted` must be bool, found {}'.format(
                        section_name, type(section['deleted'])
                    )
                    return ModuleRes(success=False, msg=errmsg)

    return ModuleRes(success=True, changed=False, meta={'all_instances': all_instances})


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = validate_config(module.params)

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
