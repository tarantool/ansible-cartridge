import os
import yaml
# import copy

import testinfra.utils.ansible_runner
import requests

from ansible.inventory.manager import InventoryManager
from ansible.vars.manager import VariableManager
from ansible.parsing.dataloader import DataLoader

ansible_runner = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
)
testinfra_hosts = ansible_runner.get_hosts('all')

APP_NAME = 'myapp'


__authorized_session = None


def get_authorized_session(cluster_cookie):
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


def get_cluster_cookie():
    inventory = InventoryManager(loader=DataLoader(), sources='hosts.yml')
    return inventory.groups['cluster'].get_vars()['cartridge_cluster_cookie']


def get_configured_instances():
    inventory = InventoryManager(loader=DataLoader(), sources='hosts.yml')
    configured_instances = {
        inventory.hosts[i].get_vars()['inventory_hostname']: inventory.hosts[i].get_vars()['config']
        for i in inventory.hosts
    }
    return configured_instances


def get_instance_vars(instance):
    inventory = InventoryManager(loader=DataLoader(), sources='hosts.yml')
    return inventory.hosts[instance].get_vars()


def get_variable_vaule(name, default=None):
    inventory = InventoryManager(loader=DataLoader(), sources='hosts.yml')
    all_group_vars = inventory.groups['cluster'].get_vars()
    return all_group_vars[name] if name in all_group_vars else default


def get_configured_replicasets():
    inventory = InventoryManager(loader=DataLoader(), sources='hosts.yml')
    variable_manager = VariableManager(loader=DataLoader(), inventory=inventory)

    replicasets = {}

    for instance in inventory.hosts:
        host_vars = variable_manager.get_vars(host=inventory.hosts[instance])
        if 'replicaset_alias' not in host_vars:
            continue

        replicaset_alias = host_vars['replicaset_alias']
        if replicaset_alias not in replicasets:
            replicasets[replicaset_alias] = {
                'instances': [],
                'leader': host_vars['leader'],
                'roles': host_vars['roles'],
            }

        replicasets[replicaset_alias]['instances'].append(instance)

    return replicasets


def get_any_instance_http_port(instances):
    return instances[list(instances.keys())[0]]['http_port']


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


def test_services_status_and_config(host):
    hostname = host.check_output('hostname -s')
    inventory = InventoryManager(loader=DataLoader(), sources='hosts.yml')

    host_instances = [
        i for i in inventory.hosts
        if hostname in list(map(lambda x:  x.name, inventory.hosts[i].get_groups()))
    ]

    default_conf = get_variable_vaule('cartridge_defaults', default={})
    default_conf.update(cluster_cookie=get_cluster_cookie())

    for instance in host_instances:
        instance_vars = get_instance_vars(instance)

        instance_conf = instance_vars['config']
        instance_name = instance_vars['inventory_hostname']

        service = host.service('{}@{}'.format(APP_NAME, instance_name))
        assert service.is_running
        assert service.is_enabled

        conf_file_path = '/etc/tarantool/conf.d/{}.{}.yml'.format(APP_NAME, instance_name)
        conf_file = host.file(conf_file_path)
        conf_section = '{}.{}'.format(APP_NAME, instance_name)

        check_conf_file(conf_file, conf_section, instance_conf)

    default_conf_file_path = '/etc/tarantool/conf.d/{}.yml'.format(APP_NAME)
    default_conf_file = host.file(default_conf_file_path)
    default_conf_file_section = APP_NAME

    check_conf_file(default_conf_file, default_conf_file_section, default_conf)


def test_instances():
    cluster_cookie = get_cluster_cookie()
    configured_instances = get_configured_instances()

    # Select one instance to be control
    admin_api_url = get_admin_api_url(configured_instances)

    # Get all started instances
    query = '''
        query {
          servers {
            uri
            alias
          }
        }
    '''
    session = get_authorized_session(cluster_cookie)
    response = session.post(admin_api_url, json={'query': query})

    started_instances = response.json()['data']['servers']
    started_instances = {i['alias']: i for i in started_instances}

    # Check if all configured instances are started and avaliable
    assert len(configured_instances) == len(started_instances)
    assert set(configured_instances.keys()) == set(started_instances.keys())
    assert all([
        configured_instances[i]['advertise_uri'] == started_instances[i]['uri']
        for i in configured_instances
    ])


def test_replicasets():
    # Get all configured instances
    configured_instances = get_configured_instances()
    cluster_cookie = get_cluster_cookie()

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
            servers {
              alias
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

    print(started_replicasets)
    configured_replicasets = get_configured_replicasets()
    print(configured_replicasets)

    # Check if started replicasets are equal to configured
    assert len(started_replicasets) == len(configured_replicasets)
    assert set(started_replicasets.keys()) == set(configured_replicasets.keys())
    for name in started_replicasets.keys():
        started_replicaset = started_replicasets[name]
        configured_replicaset = configured_replicasets[name]

        assert set(started_replicaset['roles']) == set(configured_replicaset['roles'])

        assert started_replicaset['master']['alias'] == configured_replicaset['leader']

        started_replicaset_instances = [i['alias'] for i in started_replicaset['servers']]
        assert set(started_replicaset_instances) == set(configured_replicaset['instances'])


def test_failover():
    # Get configured failover status
    configured_failover = get_variable_vaule('cartridge_failover')
    if not configured_failover:
        return

    # Get all configured instances
    configured_instances = get_configured_instances()

    if not configured_instances:
        return

    # Select one instance to be control
    admin_api_url = get_admin_api_url(configured_instances)

    # Get cluster cookie
    cluster_cookie = get_cluster_cookie()

    # Get cluster failover status
    query = '''
        query {
          cluster {
            failover
          }
        }
    '''
    session = get_authorized_session(cluster_cookie)
    response = session.post(admin_api_url, json={'query': query})

    failover = response.json()['data']['cluster']['failover']

    assert failover == configured_failover


def test_auth_params():
    # Get configured auth params
    configured_auth = get_variable_vaule('cartridge_auth')
    if not configured_auth:
        return

    # Get all configured instances
    configured_instances = get_configured_instances()
    if not configured_instances:
        return

    # Select one instance to be control
    admin_api_url = get_admin_api_url(configured_instances)

    # Get cluster cookie
    cluster_cookie = get_cluster_cookie()

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
    configured_auth = get_variable_vaule('cartridge_auth')
    if not configured_auth or 'users' not in configured_auth:
        return

    # Get all configured instances
    configured_instances = get_configured_instances()
    if not configured_instances:
        return

    # Select one instance to be control
    admin_api_url = get_admin_api_url(configured_instances)

    # Get cluster cookie
    cluster_cookie = get_cluster_cookie()

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
    specified_app_config = get_variable_vaule('cartridge_app_config')
    if not specified_app_config:
        return

    # Get all configured instances
    configured_instances = get_configured_instances()

    if not configured_instances:
        return

    # Get cluster cookie
    cluster_cookie = get_cluster_cookie()

    # Get cartridge app config
    config_url = 'http://{}:{}/admin/config'.format(
        'localhost',
        get_any_instance_http_port(configured_instances)
    )

    session = get_authorized_session(cluster_cookie)

    response = session.get(config_url)
    assert response.status_code == 200
    app_config = yaml.safe_load(response.content)

    # Check if app config is equal to configured one
    for section_name, section in specified_app_config.items():
        if section_is_deleted(section):
            assert section_name not in app_config
        else:
            assert section_name in app_config
            assert app_config[section_name] == section['body']
