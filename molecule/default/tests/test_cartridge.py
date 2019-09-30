import os
import yaml
import copy

import testinfra.utils.ansible_runner
import requests

ansible_runner = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
)
testinfra_hosts = ansible_runner.get_hosts('all')

APP_NAME = 'myapp'


__authorized_session = None


def get_authorized_session(host):
    cluster_cookie = host.ansible.get_variables()['cartridge_cluster_cookie']

    global __authorized_session
    if __authorized_session is None:
        __authorized_session = requests.Session()
        __authorized_session.auth = ('admin', cluster_cookie)

    return __authorized_session


def check_conf_file(conf_file, conf_section, conf):
    assert conf_file.exists
    assert conf_file.user == 'tarantool'
    assert conf_file.group == 'tarantool'

    conf_file_dict = yaml.load(conf_file.content_string, Loader=yaml.FullLoader)

    assert conf_section in conf_file_dict
    assert conf_file_dict[conf_section] == conf


def get_instance_alias(instance):
    return instance['alias'] if 'alias' in instance else instance['name']


def get_configured_instances():
    configured_instances = []

    for testinfra_host in testinfra_hosts:
        host_vars = ansible_runner.get_variables(testinfra_host)
        if 'cartridge_instances' in host_vars:
            configured_instances += host_vars['cartridge_instances']

    return configured_instances


def get_control_instance_admin_api_url(configured_instances):
    control_instance = configured_instances[0]
    control_instance_admin_api_url = 'http://{}:{}/admin/api'.format(
        'localhost',
        control_instance['http_port']
    )

    return control_instance_admin_api_url


def test_services_status_and_config(host):
    ansible_vars = host.ansible.get_variables()
    instances = copy.deepcopy(
        ansible_vars['cartridge_instances'] if 'cartridge_instances' in ansible_vars else []
    )
    default_conf = \
        ansible_vars['cartridge_defaults'] if 'cartridge_defaults' in ansible_vars else {}

    default_conf.update(cluster_cookie=ansible_vars['cartridge_cluster_cookie'])

    for instance in instances:
        inst_name = instance['name']

        instance_conf = {k: v for k, v in instance.items() if k != 'name'}

        service = host.service('{}@{}'.format(APP_NAME, inst_name))
        assert service.is_running
        assert service.is_enabled

        conf_file_path = '/etc/tarantool/conf.d/{}.{}.yml'.format(APP_NAME, inst_name)
        conf_file = host.file(conf_file_path)
        conf_section = '{}.{}'.format(APP_NAME, inst_name)

        check_conf_file(conf_file, conf_section, instance_conf)

    default_conf_file_path = '/etc/tarantool/conf.d/{}.yml'.format(APP_NAME)
    default_conf_file = host.file(default_conf_file_path)
    default_conf_file_section = APP_NAME

    check_conf_file(default_conf_file, default_conf_file_section, default_conf)


def test_instances(host):
    # Get all configured instances
    configured_instances = get_configured_instances()

    if not configured_instances:
        return

    # Select one instance to be control
    control_instance_admin_api_url = get_control_instance_admin_api_url(configured_instances)

    # Get all started instances
    query = '''
        query {
          servers {
            uuid
            uri
            alias
            status
            replicaset {
              uuid
            }
          }
        }
    '''
    session = get_authorized_session(host)
    response = session.post(control_instance_admin_api_url, json={'query': query})

    started_instances = response.json()['data']['servers']
    started_instances = {i['alias']: i for i in started_instances}

    # Check if all configyred instances are started and avaliable
    assert len(configured_instances) == len(started_instances)
    for configured_instance in configured_instances:
        assert get_instance_alias(configured_instance) in started_instances


def test_replicasets(host):
    # Get all configured instances
    configured_instances = get_configured_instances()

    if not configured_instances:
        return

    # Select one instance to be control
    control_instance_admin_api_url = get_control_instance_admin_api_url(configured_instances)
    # Get started replicasets
    query = '''
        query {
          replicasets {
            alias
            roles
            servers {
              alias
            }
            master {
              alias
            }
          }
        }
    '''
    session = get_authorized_session(host)
    response = session.post(control_instance_admin_api_url, json={'query': query})

    started_replicasets = response.json()['data']['replicasets']
    started_replicasets = {r['alias']: r for r in started_replicasets}

    # Configured replicasets
    configured_replicasets = host.ansible.get_variables()['cartridge_replicasets']
    configured_replicasets = {r['name']: r for r in configured_replicasets}

    # Check if started replicasets are equal to configured
    assert set(started_replicasets.keys()) == set(configured_replicasets.keys())
    for name in started_replicasets.keys():
        started_replicaset = started_replicasets[name]
        configured_replicaset = configured_replicasets[name]

        assert set(started_replicaset['roles']) == set(configured_replicaset['roles'])

        if 'leader' not in configured_replicaset:
            configured_replicaset['leader'] = configured_replicaset['instances'][0]

        assert started_replicaset['master']['alias'] == configured_replicaset['leader']

        started_replicaset_instances = [i['alias'] for i in started_replicaset['servers']]
        assert set(started_replicaset_instances) == set(configured_replicaset['instances'])


def test_failover(host):
    # Get configured failover status
    configured_failover = host.ansible.get_variables()['cartridge_failover']

    # Get all configured instances
    configured_instances = get_configured_instances()

    if not configured_instances:
        return

    # Select one instance to be control
    control_instance_admin_api_url = get_control_instance_admin_api_url(configured_instances)

    # Get cluster failover status
    query = '''
        query {
          cluster {
            failover
          }
        }
    '''
    session = get_authorized_session(host)
    response = session.post(control_instance_admin_api_url, json={'query': query})

    failover = response.json()['data']['cluster']['failover']

    assert failover == configured_failover


def test_auth_params(host):
    # Get configured auth params
    configured_auth = host.ansible.get_variables()['cartridge_auth']

    # Get all configured instances
    configured_instances = get_configured_instances()

    if not configured_instances:
        return

    # Select one instance to be control
    control_instance_admin_api_url = get_control_instance_admin_api_url(configured_instances)

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

    session = get_authorized_session(host)
    response = session.post(control_instance_admin_api_url, json={'query': query})

    auth = response.json()['data']['cluster']['auth_params']

    for key in ['enabled', 'cookie_max_age', 'cookie_renew_age']:
        if key in configured_auth:
            assert auth[key] == configured_auth[key]


def test_auth_users(host):
    # Get configured auth params
    configured_auth = host.ansible.get_variables()['cartridge_auth']

    if 'users' not in configured_auth:
        return

    # Get all configured instances
    configured_instances = get_configured_instances()

    if not configured_instances:
        return

    # Select one instance to be control
    control_instance_admin_api_url = get_control_instance_admin_api_url(configured_instances)

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

    session = get_authorized_session(host)
    response = session.post(control_instance_admin_api_url, json={'query': query})

    auth_users = response.json()['data']['cluster']['users']
    auth_users = {u['username']: u for u in auth_users if u['username'] != 'admin'}
    configured_users = {u['username']: u for u in configured_auth['users']}

    assert auth_users.keys() == configured_users.keys()
    for k in auth_users.keys():
        conf_user = configured_users[k]
        user = auth_users[k]

        for p in ['fullname', 'email']:
            if p in conf_user:
                assert user[p] == conf_user[p]
