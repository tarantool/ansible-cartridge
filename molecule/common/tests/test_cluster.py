import functools

import requests
from yaml import CLoader as Loader

import utils

testinfra_hosts = utils.get_testinfra_hosts()


def get_configured_replicasets():
    inventory = utils.get_inventory()

    replicasets = {}

    for instance in inventory.get_hosts():
        instance_vars = utils.get_instance_vars(instance)
        if 'replicaset_alias' not in instance_vars:
            continue

        if utils.instance_is_expelled(instance_vars) or utils.instance_is_stateboard(instance_vars):
            continue

        replicaset_alias = instance_vars['replicaset_alias']
        if replicaset_alias not in replicasets:
            replicasets[replicaset_alias] = {
                'instances': [],
                'failover_priority': instance_vars.get('failover_priority'),
                'roles': instance_vars['roles'],
                'all_rw': instance_vars.get('all_rw'),
                'weight': instance_vars.get('weight'),
                'vshard_group': instance_vars.get('vshard_group')
            }

        replicasets[replicaset_alias]['instances'].append(instance.get_name())

    return replicasets


def get_deps_by_roles(admin_api_url):
    query = '''
        query {
            cluster {
                known_roles {
                    name
                    dependencies
                }
            }
        }
    '''

    session = utils.get_authorized_session()
    response = session.post(admin_api_url, json={'query': query})
    data = utils.get_response_data(response)

    known_roles = data['cluster']['known_roles']

    return {r['name']: r['dependencies'] for r in known_roles}


def user_is_deleted(user):
    return 'deleted' in user and user['deleted'] is True


def section_is_deleted(section):
    return 'deleted' in section and section['deleted'] is True


def aliases_in_priority_order(replicaset_servers):
    return [s['alias'] for s in sorted(replicaset_servers, key=lambda x: x['priority'])]


def test_replicasets():
    # Get all configured instances
    configured_instances = utils.get_configured_instances()

    if not configured_instances:
        return

    # Select one instance to be control
    admin_api_url = utils.get_admin_api_url()

    # Get started replicasets
    query = '''
        query {
          replicasets {
            alias
            roles
            all_rw
            weight
            vshard_group
            servers {
              alias
              priority
            }
            master {
              alias
            }
          }
        }
    '''
    session = utils.get_authorized_session()
    response = session.post(admin_api_url, json={'query': query})
    data = utils.get_response_data(response)

    started_replicasets = data['replicasets']
    started_replicasets = {r['alias']: r for r in started_replicasets}

    configured_replicasets = get_configured_replicasets()
    deps_by_roles = get_deps_by_roles(admin_api_url)

    # Check if started replicasets are equal to configured
    assert len(started_replicasets) == len(configured_replicasets)
    assert set(started_replicasets.keys()) == set(configured_replicasets.keys())
    for name in started_replicasets.keys():
        started_replicaset = started_replicasets[name]
        configured_replicaset = configured_replicasets[name]

        exp_roles = list(functools.reduce(
            lambda roles, role: roles + deps_by_roles[role],
            started_replicaset['roles'],
            started_replicaset['roles'],
        ))
        assert set(started_replicaset['roles']) == set(exp_roles)

        started_replicaset_instances = [i['alias'] for i in started_replicaset['servers']]
        assert set(started_replicaset_instances) == set(configured_replicaset['instances'])

        if configured_replicaset['failover_priority'] is not None:
            configured_failover_priority = configured_replicaset['failover_priority']
            assert started_replicaset['master']['alias'] == configured_failover_priority[0]

            failover_priority = aliases_in_priority_order(started_replicaset['servers'])
            assert failover_priority[:len(configured_failover_priority)] == configured_failover_priority

        if configured_replicaset['all_rw'] is not None:
            assert started_replicaset['all_rw'] == configured_replicaset['all_rw']

        if configured_replicaset['weight'] is not None:
            assert started_replicaset['weight'] == configured_replicaset['weight']

        if configured_replicaset['vshard_group'] is not None:
            assert started_replicaset['vshard_group'] == configured_replicaset['vshard_group']


def test_failover():
    # Get configured failover status
    configured_failover_params = utils.get_cluster_var('cartridge_failover_params')
    if not configured_failover_params:
        return

    # Get all configured instances
    configured_instances = utils.get_configured_instances()

    if not configured_instances:
        return

    # Select one instance to be control
    admin_api_url = utils.get_admin_api_url()

    # Get cluster failover status
    query = '''
        query {
          cluster {
            failover_params {
                mode
                state_provider
                tarantool_params {
                    uri
                    password
                }
                failover_timeout
                fencing_enabled
                fencing_timeout
                fencing_pause
            }
          }
        }
    '''
    session = utils.get_authorized_session()
    response = session.post(admin_api_url, json={'query': query})
    data = utils.get_response_data(response)

    failover_params = data['cluster']['failover_params']

    failover_params_names = [
        'failover_timeout',
        'fencing_enabled',
        'fencing_timeout',
        'fencing_pause',
    ]

    for param_name in failover_params_names:
        if param_name in configured_failover_params:
            assert failover_params[param_name] == configured_failover_params[param_name]

    assert failover_params['mode'] == configured_failover_params['mode']
    if configured_failover_params.get('state_provider') is not None:
        if configured_failover_params['state_provider'] == 'stateboard':
            assert failover_params['state_provider'] == 'tarantool'

            if configured_failover_params.get('stateboard_params') is not None:
                assert 'tarantool_params' in failover_params
                configured_stateboard_params = configured_failover_params['stateboard_params']
                stateboard_params = failover_params['tarantool_params']
                for p in ['uri', 'password']:
                    if configured_stateboard_params.get(p) is not None:
                        assert stateboard_params[p] == configured_stateboard_params[p]


def test_auth_params():
    # Get configured auth params
    configured_auth = utils.get_cluster_var('cartridge_auth')
    if not configured_auth:
        return

    # Get all configured instances
    configured_instances = utils.get_configured_instances()
    if not configured_instances:
        return

    # Select one instance to be control
    admin_api_url = utils.get_admin_api_url()

    # Get cluster auth params
    query = '''
        query {
            cluster {
                auth_params {
                    enabled
                    cookie_max_age
                    cookie_renew_age
                }
            }
        }
    '''

    session = utils.get_authorized_session()
    response = session.post(admin_api_url, json={'query': query})
    data = utils.get_response_data(response)

    auth = data['cluster']['auth_params']

    for key in ['enabled', 'cookie_max_age', 'cookie_renew_age']:
        if key in configured_auth:
            assert auth[key] == configured_auth[key]


def test_auth_users():
    # Get configured auth params
    configured_auth = utils.get_cluster_var('cartridge_auth')
    if not configured_auth or 'users' not in configured_auth:
        return

    # Get all configured instances
    configured_instances = utils.get_configured_instances()
    if not configured_instances:
        return

    # Select one instance to be control
    admin_api_url = utils.get_admin_api_url()

    # Get cluster auth params
    query = '''
        query {
            cluster {
                users {
                    username
                    fullname
                    email
                }
            }
        }
    '''

    session = utils.get_authorized_session()
    response = session.post(admin_api_url, json={'query': query})
    data = utils.get_response_data(response)

    auth_users = data['cluster']['users']
    auth_users = {
        u['username']: u for u in auth_users
        if u['username'] != 'admin' and not user_is_deleted(u)
    }
    configured_users = {u['username']: u for u in configured_auth['users']}

    assert auth_users.keys() == configured_users.keys()
    for k in auth_users.keys():
        conf_user = configured_users[k]
        user = auth_users[k]

        for p in ['fullname', 'email']:
            if p in conf_user:
                assert user[p] == conf_user[p]

    # Check if all users can log in
    login_url = '%s/login' % utils.get_any_instance_url()

    for username, user in configured_users.items():
        if 'password' not in user:
            continue

        response = requests.post(login_url, json={'username': username, 'password': user['password']})
        assert response.status_code == 200


def test_app_config():
    # Get configured auth params
    specified_app_config = utils.get_cluster_var('cartridge_app_config')
    if not specified_app_config:
        return

    # Get all configured instances
    configured_instances = utils.get_configured_instances()

    if not configured_instances:
        return

    # Get cartridge app config
    config_url = '%s/admin/config' % utils.get_any_instance_url()
    session = utils.get_authorized_session()

    response = session.get(config_url)
    assert response.status_code == 200

    loader = Loader(response.content)
    app_config = loader.get_data()

    # Check if app config is equal to configured one
    for section_name, section in specified_app_config.items():
        if section_is_deleted(section):
            assert section_name not in app_config
        else:
            assert section_name in app_config
            assert app_config[section_name] == section['body']


def test_cluster_has_no_issues():
    # Get all configured instances
    configured_instances = utils.get_configured_instances()
    if not configured_instances:
        return

    # Select one instance to be control
    admin_api_url = utils.get_admin_api_url()

    # Get cluster auth params
    query = '''
        query {
            cluster {
                issues {
                    topic
                    message
                }
            }
        }
    '''

    session = utils.get_authorized_session()
    response = session.post(admin_api_url, json={'query': query})
    data = utils.get_response_data(response)

    issues = data['cluster']['issues']

    assert len(issues) == 0, 'Found issues: %s' % ', '.join([
        '%s: %s' % (issue['topic'], issue['message'])
        for issue in issues
    ])
