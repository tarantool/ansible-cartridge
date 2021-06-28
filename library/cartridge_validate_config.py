#!/usr/bin/env python

import os
import re

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'play_hosts': {'required': True, 'type': 'list'},
    'module_hostvars': {'required': True, 'type': 'dict'}
}

INSTANCE_REQUIRED_PARAMS = ['cartridge_app_name', 'config']
PARAMS_THE_SAME_FOR_ALL_HOSTS = [
    'cartridge_app_name',
    'cartridge_cluster_cookie',
    'cartridge_not_save_cookie_in_app_config',
    'cartridge_auth',
    'cartridge_bootstrap_vshard',
    'bootstrap_vshard_retries',
    'bootstrap_vshard_delay',
    'connect_to_membership_retries',
    'connect_to_membership_delay',
    'cartridge_failover',
    'cartridge_failover_params',
    'cartridge_app_config',
    'cartridge_scenario',
    'cartridge_custom_steps_dir',
    'cartridge_custom_steps',
    'cartridge_failover_promote_params',
    'twophase_netbox_call_timeout',
    'twophase_upload_config_timeout',
    'twophase_apply_config_timeout',
    'edit_topology_timeout',
    'edit_topology_healthy_timeout',
    'edit_topology_allow_missed_instances',
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

FALOVER_MODES = [
    'stateful',
    'eventual',
    'disabled',
]

STATEFUL_FAILOVER_PARAMS = [
    'state_provider',
    'stateboard_params',
    'etcd2_params',
]

STATEFUL_FAILOVER_REQUIRED_PARAMS = [
    'state_provider',
]

STATEFUL_FAILOVER_STATE_PROVIDERS = [
    'stateboard',
    'etcd2',
]

STATEBOARD_PROVIDER_REQUIRED_PARAMS = [
    'uri',
    'password',
]

ETCD2_PROVIDER_REQUIRED_PARAMS = [
    'prefix',
]

STATEBOARD_CONFIG_REQUIRED_PARAMS = [
    'listen',
    'password',
]

ALLOWED_FAILOVER_PROMOTE_PARAMS = [
    'replicaset_leaders',
    'force_inconsistency',
]

SCHEMA = {
    'cartridge_package_path': str,
    'cartridge_app_name': str,
    'cartridge_cluster_cookie': str,
    'cartridge_not_save_cookie_in_app_config': bool,
    'cartridge_runtime_params': dict,
    'cartridge_defaults': dict,
    'cartridge_bootstrap_vshard': bool,
    'bootstrap_vshard_retries': int,
    'bootstrap_vshard_delay': int,
    'connect_to_membership_retries': int,
    'connect_to_membership_delay': int,
    'cartridge_wait_buckets_discovery': bool,
    'cartridge_failover': bool,
    'cartridge_app_config': dict,
    'cartridge_scenario': list,
    'cartridge_custom_steps_dir': str,
    'cartridge_custom_steps': list,
    'cartridge_scenario_name': str,
    'cartridge_custom_scenarios': dict,
    'restarted': bool,
    'expelled': bool,
    'stateboard': bool,
    'cartridge_multiversion': bool,
    'instance_start_timeout': int,
    'instance_start_retries': int,
    'instance_start_delay': int,
    'instance_discover_buckets_timeout': int,
    'instance_discover_buckets_retries': int,
    'instance_discover_buckets_delay': int,
    'twophase_netbox_call_timeout': int,
    'twophase_upload_config_timeout': int,
    'twophase_apply_config_timeout': int,
    'edit_topology_timeout': int,
    'edit_topology_healthy_timeout': int,
    'edit_topology_allow_missed_instances': bool,
    'replicaset_alias': str,
    'failover_priority': [str],
    'roles': [str],
    'all_rw': bool,
    'weight': int,
    'vshard_group': str,
    'cartridge_enable_tarantool_repo': bool,
    'cartridge_conf_dir': str,
    'cartridge_run_dir': str,
    'cartridge_data_dir': str,
    'cartridge_app_user': str,
    'cartridge_app_group': str,
    'cartridge_app_install_dir': str,
    'cartridge_app_instances_dir': str,
    'cartridge_delivered_package_path': str,
    'cartridge_control_instance': dict,
    'cartridge_memtx_dir_parent': str,
    'cartridge_vinyl_dir_parent': str,
    'cartridge_wal_dir_parent': str,
    'cartridge_configure_systemd_unit_files': bool,
    'cartridge_systemd_dir': str,
    'cartridge_configure_tmpfiles': bool,
    'cartridge_tmpfiles_dir': str,
    'cartridge_install_tarantool_for_tgz': bool,
    'cartridge_keep_num_latest_dists': int,
    'cartridge_remove_temporary_files': bool,
    'cartridge_paths_to_keep_on_cleanup': list,
    'zone': str,
    'cartridge_extra_env': dict,
    'cartridge_eval_body': str,
    'cartridge_eval_file': str,
    'cartridge_eval_args': list,
    'cartridge_eval_with_retries': bool,
    'cartridge_eval_retries': int,
    'cartridge_eval_delay': int,
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
    'cartridge_failover_params': {
        'enabled': bool,
        'mode': str,
        'state_provider': str,
        'stateboard_params': {
            'uri': str,
            'password': str
        },
        'etcd2_params': {
            'prefix': str,
            'lock_delay': int,
            'endpoints': [str],
            'username': str,
            'password': str,
        },
        'failover_timeout': int,
        'fencing_enabled': bool,
        'fencing_timeout': int,
        'fencing_pause': int,
    },
    'cartridge_failover_promote_params': {
        'replicaset_leaders': dict,
        'force_inconsistency': bool,
    },
    'allowed_members_states': [str],
    'wait_members_alive_retries': int,
    'wait_members_alive_delay': int,
    'allow_warning_issues': bool,
    'show_issues': bool,
    'wait_cluster_has_no_issues_retries': int,
    'wait_cluster_has_no_issues_delay': int,
}


def is_valid_advertise_uri(uri):
    rgx = re.compile(r'^\S+:\d+$')
    return re.match(rgx, uri) is not None


def check_schema(schema, conf, path=''):
    if conf is None:
        return None
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
        if not isinstance(conf, schema):
            return '{} must be {}'.format(path, schema)
        return None
    else:
        return 'Wrong type'


def validate_types(all_vars):
    return check_schema(SCHEMA, all_vars)


def check_cluster_cookie_symbols(cluster_cookie):
    if cluster_cookie is None:
        return None

    if len(cluster_cookie) > CLUSTER_COOKIE_MAX_LEN:
        errmsg = 'Cluster cookie cannot be longer than {}'.format(CLUSTER_COOKIE_MAX_LEN)
        return errmsg

    m = re.search(CLUSTER_COOKIE_FORBIDDEN_SYMBOLS_RGX, cluster_cookie)
    if m is not None:
        errmsg = 'Cluster cookie cannot contain symbols other than [a-zA-Z0-9_.~-] ' + \
                 '("{}" found)'.format(m.group())
        return errmsg

    return None


def check_required_params(instance_vars, host):
    for p in INSTANCE_REQUIRED_PARAMS:
        if instance_vars.get(p) is None:
            errmsg = '"{}" must be specified (missed for "{}")'.format(p, host)
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


def check_params_the_same_for_all_hosts(instance_vars, found_common_params):
    for p in PARAMS_THE_SAME_FOR_ALL_HOSTS:
        if found_common_params.get(p) is not None:
            if instance_vars.get(p) != found_common_params.get(p):
                errmsg = '"{}" must be the same for all hosts'.format(p)
                return errmsg
        elif instance_vars.get(p) is not None:
            found_common_params[p] = instance_vars.get(p)

    return None


def check_replicaset(instance_vars, found_replicasets):
    if 'replicaset_alias' not in instance_vars:
        return None

    replicaset_alias = instance_vars['replicaset_alias']

    replicaset = {p: instance_vars.get(p) for p in REPLICASET_PARAMS}

    if replicaset_alias not in found_replicasets:
        for p in REPLICASET_REQUIRED_PARAMS:
            if p not in instance_vars:
                errmsg = 'Parameter "{}" is required for all replicasets (missed for "{}")'.format(
                    p, replicaset_alias
                )
                return errmsg
        # Save replicaset info
        found_replicasets[replicaset_alias] = replicaset
    else:
        if replicaset != found_replicasets[replicaset_alias]:
            errmsg = 'Replicaset parameters must be the same for all instances' + \
                     ' within one replicaset ("{}")'.format(replicaset_alias)
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


def check_stateboard(stateboard_vars):
    if stateboard_vars.get('expelled') is True:
        return '"expelled" flag can\'t be used for stateboard instance'

    for p in REPLICASET_PARAMS:
        if stateboard_vars.get(p) is not None:
            return '"{}" flag can\'t be used for stateboard instance'.format(p)

    if stateboard_vars.get('config') is None:
        return '"config" parameter is required for stateboard instance'

    if stateboard_vars.get('cartridge_app_name') is None:
        return '"cartridge_app_name" parameter is required for stateboard instance'

    # Check if all required params are specified
    stateboard_config = stateboard_vars['config']
    for p in STATEBOARD_CONFIG_REQUIRED_PARAMS:
        if stateboard_config.get(p) is None:
            return 'Missed required parameter "{}" in stateboard config'.format(p)

    # Check if no forbidden params specified
    for p in CONFIG_FORBIDDEN_PARAMS:
        if stateboard_config.get(p) is not None:
            return 'Specified forbidden parameter "{}" in stateboard config'.format(p)

    # Check stateboard URI
    stateboard_uri = stateboard_config['listen']
    if not is_valid_advertise_uri(stateboard_uri):
        return 'Stateboard listen URI must be specified as "<host>:<port>"'

    # Check stateboard password
    stateboard_password = stateboard_config['password']
    m = re.search(CLUSTER_COOKIE_FORBIDDEN_SYMBOLS_RGX, stateboard_password)
    if m is not None:
        errmsg = 'Stateboard password cannot contain symbols other than [a-zA-Z0-9_.~-] ' + \
                 '("{}" found)'.format(m.group())
        return errmsg

    return None


def check_failover(found_common_params):
    cartridge_failover = found_common_params.get('cartridge_failover')
    cartridge_failover_params = found_common_params.get('cartridge_failover_params')

    if cartridge_failover is not None and cartridge_failover_params is not None:
        return 'Only one of "cartridge_failover" and "cartridge_failover_params" can be specified'

    if cartridge_failover_params is not None:
        if cartridge_failover_params.get('mode') is None:
            return '"mode" is required in "cartridge_failover_params"'

        mode = cartridge_failover_params['mode']
        if mode not in FALOVER_MODES:
            return 'Failover Failover mode should be one of {}'.format(FALOVER_MODES)

        if mode == 'disabled':  # don't check other parameters
            return None

        if mode == 'eventual':
            for p in STATEFUL_FAILOVER_PARAMS:
                if p in cartridge_failover_params:
                    return '"{}" failover parameter is allowed only for "stateful" mode'.format(p)

        if mode == 'stateful':
            for p in STATEFUL_FAILOVER_REQUIRED_PARAMS:
                if p not in cartridge_failover_params:
                    return '"{}" failover parameter is required for "stateful" mode'.format(p)

            if cartridge_failover_params['state_provider'] not in STATEFUL_FAILOVER_STATE_PROVIDERS:
                return "Stateful failover state provider should be one of {}".format(
                    STATEFUL_FAILOVER_STATE_PROVIDERS
                )

            if cartridge_failover_params['state_provider'] == 'stateboard':
                if cartridge_failover_params.get('stateboard_params') is None:
                    return '"stateboard_params" is required for "stateboard" state provider'

                for p in STATEBOARD_PROVIDER_REQUIRED_PARAMS:
                    if p not in cartridge_failover_params['stateboard_params']:
                        return '"stateboard_params.{}" is required for "stateboard" provider'.format(p)

                state_provider_uri = cartridge_failover_params['stateboard_params']['uri']
                if not is_valid_advertise_uri(state_provider_uri):
                    return 'Stateboard URI must be specified as "<host>:<port>"'

                state_provider_password = cartridge_failover_params['stateboard_params']['password']

                m = re.search(CLUSTER_COOKIE_FORBIDDEN_SYMBOLS_RGX, state_provider_password)
                if m is not None:
                    errmsg = 'Stateboard password cannot contain symbols other than [a-zA-Z0-9_.~-] ' + \
                             '("{}" found)'.format(m.group())
                    return errmsg

            elif cartridge_failover_params['state_provider'] == 'etcd2':
                etcd2_params = cartridge_failover_params.get('etcd2_params')
                if etcd2_params is not None and etcd2_params.get('endpoints') is not None:
                    for endpoint in etcd2_params['endpoints']:
                        if not is_valid_advertise_uri(endpoint):
                            return 'etcd2 endpoints must be specified as "<host>:<port>"'

    return None


def check_scenario(found_common_params):
    scenario = found_common_params.get('cartridge_scenario')
    if scenario is not None:
        for task in scenario:
            if type(task) != str:
                return "Incorrect type of task name '%s'. String expected, got: %s" % (task, type(task))

    dir_path = found_common_params.get('cartridge_custom_steps_dir')
    if dir_path is not None:
        if not os.path.exists(dir_path):
            return "Directory '%s' from 'cartridge_custom_steps_dir' doesn't exists" % dir_path

    custom_steps = found_common_params.get('cartridge_custom_steps')
    if custom_steps is not None:
        for task in custom_steps:
            if type(task) != dict:
                return "Incorrect type of custom task '%s'. Dictionary expected, got: %s" % (task, type(task))

            if task.get('name') is not None and type(task.get('name')) != str:
                return "Incorrect type of name from task '%s'. String expected, got: %s" % (task, type(task['name']))

            if not task.get('file'):
                return "No path to task file in custom task '%s'" % task
            if type(task['file']) != str:
                return "Incorrect type of file path from task '%s'. String expected, got: %s" % (
                    task, type(task['file'])
                )
            if not os.path.exists(task['file']):
                return "File '%s' from custom task '%s' doesn't exists" % (task['file'], task)


def check_failover_promote_params(found_common_params):
    failover_promote_params = found_common_params.get('cartridge_failover_promote_params')
    if failover_promote_params is None:
        return None

    for p in failover_promote_params:
        if p not in ALLOWED_FAILOVER_PROMOTE_PARAMS:
            return "Passed unknown failover promote parameter: '%s'" % p

    replicaset_leaders = failover_promote_params.get('replicaset_leaders')
    if replicaset_leaders is not None:
        if not all([isinstance(k, str) and isinstance(v, str) for k, v in replicaset_leaders.items()]):
            return "Variable 'replicaset_leaders' should be of type map(string -> string)"


def validate_config(params):
    found_replicasets = {}
    found_common_params = {}

    warnings = []

    for host in params['play_hosts']:
        instance_vars = params['module_hostvars'][host]

        if instance_vars.get('edit_topology_timeout') is not None:
            warnings.append(
                "Variable 'edit_topology_timeout' is deprecated since 1.9.0 and will be removed in 2.0.0. "
                "Use 'edit_topology_healthy_timeout' instead."
            )
        if instance_vars.get('instance_start_timeout') is not None:
            warnings.append(
                "Variable 'instance_start_timeout' is deprecated since 1.10.0 and will be removed in 2.0.0. "
                "Use 'instance_start_retries' and 'instance_start_delay' instead."
            )
        if instance_vars.get('instance_discover_buckets_timeout') is not None:
            warnings.append(
                "Variable 'instance_discover_buckets_timeout' is deprecated since 1.10.0 and will be removed in 2.0.0. "
                "Use 'instance_discover_buckets_retries' and 'instance_discover_buckets_delay' instead."
            )

        # Validate types
        errmsg = validate_types(instance_vars)
        if errmsg is not None:
            return helpers.ModuleRes(failed=True, msg=errmsg)

        if instance_vars.get('stateboard') is True:
            errmsg = check_stateboard(instance_vars)
            if errmsg is not None:
                return helpers.ModuleRes(failed=True, msg=errmsg)
            continue

        # All required params should be specified
        errmsg = check_required_params(instance_vars, host)
        if errmsg is not None:
            return helpers.ModuleRes(failed=True, msg=errmsg)

        errmsg = check_cluster_cookie_symbols(instance_vars.get('cartridge_cluster_cookie'))
        if errmsg is not None:
            return errmsg

        # Instance config
        errmsg = check_instance_config(instance_vars['config'], host)
        if errmsg is not None:
            return helpers.ModuleRes(failed=True, msg=errmsg)

        # Params common for all instances
        errmsg = check_params_the_same_for_all_hosts(instance_vars, found_common_params)
        if errmsg is not None:
            return helpers.ModuleRes(failed=True, msg=errmsg)

        # Cartridge defaults
        if 'cartridge_defaults' in instance_vars:
            if 'cluster_cookie' in instance_vars['cartridge_defaults']:
                errmsg = 'Cluster cookie must be specified in "cartridge_cluster_cookie", not in "cartridge_defaults"'
                return helpers.ModuleRes(failed=True, msg=errmsg)

        # Instance state
        if instance_vars.get('expelled') is True and instance_vars.get('restarted') is True:
            errmsg = 'Flags "expelled" and "restarted" cannot be set at the same time'
            return helpers.ModuleRes(failed=True, msg=errmsg)

        # Replicasets
        errmsg = check_replicaset(instance_vars, found_replicasets)
        if errmsg is not None:
            return helpers.ModuleRes(failed=True, msg=errmsg)

        # Dist retention
        if 'cartridge_keep_num_latest_dists' in instance_vars:
            keep_num_latest_dists = instance_vars['cartridge_keep_num_latest_dists']
            if keep_num_latest_dists <= 0:
                errmsg = '"cartridge_keep_num_latest_dists" should be greater than 0'
                return helpers.ModuleRes(failed=True, msg=errmsg)
            if keep_num_latest_dists == 1:
                warnings.append(
                    "Using 'cartridge_keep_num_latest_dists' equals to 1 can be dangerous. "
                    "Make sure that there are no instances that use old versions"
                )

    # Authorization params
    errmsg = check_auth(found_common_params)
    if errmsg is not None:
        return helpers.ModuleRes(failed=True, msg=errmsg)

    # Clusterwide config
    errmsg = check_app_config(found_common_params)
    if errmsg is not None:
        return helpers.ModuleRes(failed=True, msg=errmsg)

    # Failover
    errmsg = check_failover(found_common_params)
    if errmsg is not None:
        return helpers.ModuleRes(failed=True, msg=errmsg)

    # Scenario
    errmsg = check_scenario(found_common_params)
    if errmsg is not None:
        return helpers.ModuleRes(failed=True, msg=errmsg)

    # Failover promote params
    errmsg = check_failover_promote_params(found_common_params)
    if errmsg is not None:
        return helpers.ModuleRes(failed=True, msg=errmsg)

    if found_common_params.get('cartridge_failover') is not None:
        warnings.append(
            "Variable 'cartridge_failover' is deprecated since 1.3.0 and will be removed in 2.0.0. "
            "Use 'cartridge_failover_params' instead."
        )

    return helpers.ModuleRes(changed=False, warnings=warnings)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, validate_config)
