import os
from yaml import CLoader as Loader

import testinfra.utils.ansible_runner
import requests

from ansible.inventory.manager import InventoryManager
from ansible.vars.manager import VariableManager
from ansible.parsing.dataloader import DataLoader

ansible_runner = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
)
testinfra_hosts = ansible_runner.get_hosts('all')

scenario_name = os.environ['MOLECULE_SCENARIO_NAME']

HOSTS_PATH = os.path.join('molecule', scenario_name, 'hosts.yml')

inventory = InventoryManager(loader=DataLoader(), sources=HOSTS_PATH)
variable_manager = VariableManager(loader=DataLoader(), inventory=inventory)

app_name = 'myapp'
if scenario_name == 'package_name':
    app_name = inventory.groups['cluster'].get_vars()['cartridge_app_name']

cluster_cookie = inventory.groups['cluster'].get_vars()['cartridge_cluster_cookie']

__authorized_session = None
__configured_instances = None


def get_authorized_session(cluster_cookie):
    global __authorized_session
    if __authorized_session is None:
        __authorized_session = requests.Session()
        __authorized_session.auth = ('admin', cluster_cookie)

    return __authorized_session


def check_conf_file(conf_file, instance_id, conf):
    assert conf_file.exists
    assert conf_file.user == 'tarantool'
    assert conf_file.group == 'tarantool'

    loader = Loader(conf_file.content_string)
    conf_file_dict = loader.get_data()

    assert instance_id in conf_file_dict
    assert conf_file_dict[instance_id] == conf


def get_configured_instances():
    global __configured_instances
    if __configured_instances is None:
        __configured_instances = {
            inventory.hosts[i].get_vars()['inventory_hostname']: inventory.hosts[i].get_vars()
            for i in inventory.hosts
        }
    return __configured_instances


def get_instance_vars(instance):
    return inventory.hosts[instance].get_vars()


def get_cluster_var(name, default=None):
    all_group_vars = inventory.groups['cluster'].get_vars()
    return all_group_vars[name] if name in all_group_vars else default


def get_configured_replicasets():
    replicasets = {}

    for instance in inventory.get_hosts():
        host_vars = variable_manager.get_vars(host=instance)
        if 'replicaset_alias' not in host_vars:
            continue

        if instance_is_expelled(host_vars) or instance_is_stateboard(host_vars):
            continue

        replicaset_alias = host_vars['replicaset_alias']
        if replicaset_alias not in replicasets:
            replicasets[replicaset_alias] = {
                'instances': [],
                'failover_priority': host_vars.get('failover_priority'),
                'roles': host_vars['roles'],
                'all_rw': host_vars.get('all_rw'),
                'weight': host_vars.get('weight'),
                'vshard_group': host_vars.get('vshard_group')
            }

        replicasets[replicaset_alias]['instances'].append(instance.get_name())

    return replicasets


def get_any_instance_http_port(instances):
    for _, instance_vars in instances.items():
        if not instance_is_expelled(instance_vars) and not instance_is_stateboard(instance_vars):
            return instance_vars['config']['http_port']
    assert False


def get_admin_api_url(instances):
    admin_url = 'http://localhost:{}'.format(get_any_instance_http_port(instances))
    admin_api_url = '{}/admin/api'.format(
        admin_url
    )

    return admin_api_url


def user_is_deleted(user):
    return 'deleted' in user and user['deleted'] is True


def section_is_deleted(section):
    return 'deleted' in section and section['deleted'] is True


def instance_is_expelled(host_vars):
    return 'expelled' in host_vars and host_vars['expelled'] is True


def instance_is_stateboard(host_vars):
    return host_vars.get('stateboard') is True


def aliases_in_priority_order(replicaset_servers):
    return [s['alias'] for s in sorted(replicaset_servers, key=lambda x: x['priority'])]


def test_services_status_and_config(host):
    hostname = host.check_output('hostname -s')

    machine_instances = [
        instance for instance in inventory.get_hosts()
        if variable_manager.get_vars(host=instance).get('ansible_host') == hostname
    ]

    assert machine_instances

    default_conf = get_cluster_var('cartridge_defaults', default={})
    default_conf.update(cluster_cookie=cluster_cookie)

    for instance in machine_instances:
        instance_vars = variable_manager.get_vars(host=instance)

        instance_conf = instance_vars['config']
        if instance_conf.get('memtx_memory') == '{{ common_memtx_memory }}':
            instance_conf['memtx_memory'] = 268436000

        instance_name = instance_vars['inventory_hostname']

        conf_dir = instance_vars.get('cartridge_conf_dir', '/etc/tarantool/conf.d')
        run_dir = instance_vars.get('cartridge_run_dir', '/var/run/tarantool')
        data_dir = instance_vars.get('cartridge_data_dir', '/var/lib/tarantool')

        install_dir = instance_vars.get('cartridge_app_install_dir', '/usr/share/tarantool')
        instances_dir = instance_vars.get('cartridge_app_instances_dir', '/usr/share/tarantool')

        multiversion = instance_vars.get('cartridge_multiversion', False)

        if not multiversion:
            dist_dir_path = os.path.join(install_dir, app_name)
        else:
            package_path = instance_vars.get('cartridge_package_path')
            package_basename = os.path.basename(package_path)
            package_name_version, ext = os.path.splitext(package_basename)
            if ext == '.gz' and package_name_version.endswith('.tar'):
                package_name_version, _ = os.path.splitext(package_name_version)

            dist_dir_path = os.path.join(install_dir, package_name_version)

        dist_dir = host.file(dist_dir_path)
        assert dist_dir.exists

        if not instance_is_stateboard(instance_vars):
            service_name = '%s@%s' % (app_name, instance_name)
            instance_id = '%s.%s' % (app_name, instance_name)
        else:
            instance_id = service_name = '%s-stateboard' % app_name

        if multiversion:
            instance_dist_dir = host.file(os.path.join(instances_dir, instance_id))
            assert instance_dist_dir.exists
            assert instance_dist_dir.is_symlink
            assert instance_dist_dir.linked_to == dist_dir_path

        conf_file = host.file(os.path.join(conf_dir, '%s.yml' % instance_id))
        instance_id = instance_id

        default_conf_file = host.file(os.path.join(conf_dir, '%s.yml' % app_name))
        default_conf_section = app_name

        pid_file = host.file(os.path.join(run_dir, '%s.pid' % instance_id))
        console_sock_file = host.file(os.path.join(run_dir, '%s.control' % instance_id))
        work_dir_file = host.file(os.path.join(data_dir, instance_id))

        service = host.service(service_name)

        if instance_is_expelled(instance_vars):
            assert not service.is_running
            assert not service.is_enabled

            assert not conf_file.exists

            assert not pid_file.exists
            assert not console_sock_file.exists
            assert not work_dir_file.exists
        else:
            assert service.is_running
            assert service.is_enabled

            check_conf_file(conf_file, instance_id, instance_conf)

    check_conf_file(default_conf_file, default_conf_section, default_conf)


def test_instances():
    configured_instances = get_configured_instances()

    # Select one instance to be control
    admin_api_url = get_admin_api_url(configured_instances)

    # Get all started instances
    query = '''
        query {
          servers {
            uri
            alias
            zone
          }
        }
    '''
    session = get_authorized_session(cluster_cookie)
    response = session.post(admin_api_url, json={'query': query})

    started_instances = response.json()['data']['servers']
    started_instances = {i['alias']: i for i in started_instances}

    # filter out expelled instances and stateboard
    configured_instances = {
        i: instance_vars for i, instance_vars in configured_instances.items()
        if not instance_is_expelled(instance_vars) and not instance_is_stateboard(instance_vars)
    }

    # Check if all configured instances are started and avaliable
    assert len(configured_instances) == len(started_instances)
    assert set(configured_instances.keys()) == set(started_instances.keys())
    assert all([
        configured_instances[i]['config']['advertise_uri'] == started_instances[i]['uri']
        for i in configured_instances
    ])

    assert all([
        configured_instances[i].get('zone') == started_instances[i]['zone']
        for i in configured_instances
    ])


def test_replicasets():
    # Get all configured instances
    configured_instances = get_configured_instances()

    if not configured_instances:
        return

    # Select one instance to be control
    admin_api_url = get_admin_api_url(configured_instances)

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
    session = get_authorized_session(cluster_cookie)
    response = session.post(admin_api_url, json={'query': query})

    started_replicasets = response.json()['data']['replicasets']
    started_replicasets = {r['alias']: r for r in started_replicasets}

    configured_replicasets = get_configured_replicasets()

    # Check if started replicasets are equal to configured
    assert len(started_replicasets) == len(configured_replicasets)
    assert set(started_replicasets.keys()) == set(configured_replicasets.keys())
    for name in started_replicasets.keys():
        started_replicaset = started_replicasets[name]
        configured_replicaset = configured_replicasets[name]

        assert set(started_replicaset['roles']) == set(configured_replicaset['roles'])

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
    configured_failover_params = get_cluster_var('cartridge_failover_params')
    if not configured_failover_params:
        return

    # Get all configured instances
    configured_instances = get_configured_instances()

    if not configured_instances:
        return

    # Select one instance to be control
    admin_api_url = get_admin_api_url(configured_instances)

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
    session = get_authorized_session(cluster_cookie)
    response = session.post(admin_api_url, json={'query': query})

    failover_params = response.json()['data']['cluster']['failover_params']

    FAILOVER_PARAMS = [
        'failover_timeout',
        'fencing_enabled',
        'fencing_timeout',
        'fencing_pause',
    ]

    for param_name in FAILOVER_PARAMS:
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
    configured_auth = get_cluster_var('cartridge_auth')
    if not configured_auth:
        return

    # Get all configured instances
    configured_instances = get_configured_instances()
    if not configured_instances:
        return

    # Select one instance to be control
    admin_api_url = get_admin_api_url(configured_instances)

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

    session = get_authorized_session(cluster_cookie)
    response = session.post(admin_api_url, json={'query': query})

    auth = response.json()['data']['cluster']['auth_params']

    for key in ['enabled', 'cookie_max_age', 'cookie_renew_age']:
        if key in configured_auth:
            assert auth[key] == configured_auth[key]


def test_auth_users():
    # Get configured auth params
    configured_auth = get_cluster_var('cartridge_auth')
    if not configured_auth or 'users' not in configured_auth:
        return

    # Get all configured instances
    configured_instances = get_configured_instances()
    if not configured_instances:
        return

    # Select one instance to be control
    admin_api_url = get_admin_api_url(configured_instances)

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

    session = get_authorized_session(cluster_cookie)
    response = session.post(admin_api_url, json={'query': query})

    auth_users = response.json()['data']['cluster']['users']
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
    login_url = 'http://{}:{}/login'.format(
        'localhost',
        get_any_instance_http_port(configured_instances)
    )

    for username, user in configured_users.items():
        if 'password' not in user:
            continue

        response = requests.post(login_url, json={'username': username, 'password': user['password']})
        assert response.status_code == 200


def test_app_config():
    # Get configured auth params
    specified_app_config = get_cluster_var('cartridge_app_config')
    if not specified_app_config:
        return

    # Get all configured instances
    configured_instances = get_configured_instances()

    if not configured_instances:
        return

    # Get cartridge app config
    config_url = 'http://{}:{}/admin/config'.format(
        'localhost',
        get_any_instance_http_port(configured_instances)
    )

    session = get_authorized_session(cluster_cookie)

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
    configured_instances = get_configured_instances()
    if not configured_instances:
        return

    # Select one instance to be control
    admin_api_url = get_admin_api_url(configured_instances)

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

    session = get_authorized_session(cluster_cookie)
    response = session.post(admin_api_url, json={'query': query})
    assert response.status_code == 200

    issues = response.json()['data']['cluster']['issues']

    assert len(issues) == 0, 'Found issues: %s' % ', '.join([
        '%s: %s' % (issue['topic'], issue['message'])
        for issue in issues
    ])
