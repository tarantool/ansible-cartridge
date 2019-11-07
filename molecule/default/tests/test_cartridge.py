import os
import yaml
# import copy

import testinfra.utils.ansible_runner
import requests

from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader

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


def get_admin_api_url(configured_instances):
    admin_url = 'http://localhost:{}'.format(configured_instances[0]['http_port'])
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
    instances = inventory.hosts
    host_instances = [
        i for i in instances if hostname in list(map(lambda x:  x.name, instances[i].get_groups()))
    ]

    all_group_vars = inventory.groups['all'].get_vars()
    default_conf = \
        all_group_vars['cartridge_defaults'] if 'cartridge_defaults' in all_group_vars else {}

    default_conf.update(cluster_cookie=all_group_vars['cartridge_cluster_cookie'])

    for instance in host_instances:
        instance_vars = inventory.hosts[instance].get_vars()

        instance_conf = default_conf.copy()
        instance_conf.update(instance_vars['config'])
        instance_name = instance_vars['inventory_hostname']

        service = host.service('{}@{}'.format(APP_NAME, instance_name))
        assert service.is_running
        assert service.is_enabled

        conf_file_path = '/etc/tarantool/conf.d/{}.{}.yml'.format(APP_NAME, instance_name)
        conf_file = host.file(conf_file_path)
        conf_section = '{}.{}'.format(APP_NAME, instance_name)

        check_conf_file(conf_file, conf_section, instance_conf)

# def test_instances(host):
#     # Get all configured instances
#     configured_instances = get_configured_instances()

#     if not configured_instances:
#         return

#     # Select one instance to be control
#     admin_api_url = get_admin_api_url(configured_instances)

#     # Get all started instances
#     query = '''
#         query {
#           servers {
#             uuid
#             uri
#             alias
#             status
#             replicaset {
#               uuid
#             }
#           }
#         }
#     '''
#     session = get_authorized_session(host)
#     response = session.post(admin_api_url, json={'query': query})

#     started_instances = response.json()['data']['servers']
#     started_instances = {i['alias']: i for i in started_instances}

#     # Check if all configured instances are started and avaliable
#     assert len(configured_instances) == len(started_instances)
#     for configured_instance in configured_instances:
#         assert get_instance_alias(configured_instance) in started_instances


# def test_replicasets(host):
#     # Get all configured instances
#     configured_instances = get_configured_instances()

#     if not configured_instances:
#         return

#     # Select one instance to be control
#     admin_api_url = get_admin_api_url(configured_instances)

#     # Get started replicasets
#     query = '''
#         query {
#           replicasets {
#             alias
#             roles
#             servers {
#               alias
#             }
#             master {
#               alias
#             }
#           }
#         }
#     '''
#     session = get_authorized_session(host)
#     response = session.post(admin_api_url, json={'query': query})

#     started_replicasets = response.json()['data']['replicasets']
#     started_replicasets = {r['alias']: r for r in started_replicasets}

#     # Configured replicasets
#     configured_replicasets = host.ansible.get_variables()['cartridge_replicasets']
#     configured_replicasets = {r['name']: r for r in configured_replicasets}

#     # Check if started replicasets are equal to configured
#     assert set(started_replicasets.keys()) == set(configured_replicasets.keys())
#     for name in started_replicasets.keys():
#         started_replicaset = started_replicasets[name]
#         configured_replicaset = configured_replicasets[name]

#         assert set(started_replicaset['roles']) == set(configured_replicaset['roles'])

#         if 'leader' not in configured_replicaset:
#             configured_replicaset['leader'] = configured_replicaset['instances'][0]

#         assert started_replicaset['master']['alias'] == configured_replicaset['leader']

#         started_replicaset_instances = [i['alias'] for i in started_replicaset['servers']]
#         assert set(started_replicaset_instances) == set(configured_replicaset['instances'])


# def test_failover(host):
#     # Get configured failover status
#     configured_failover = host.ansible.get_variables()['cartridge_failover']

#     # Get all configured instances
#     configured_instances = get_configured_instances()

#     if not configured_instances:
#         return

#     # Select one instance to be control
#     admin_api_url = get_admin_api_url(configured_instances)

#     # Get cluster failover status
#     query = '''
#         query {
#           cluster {
#             failover
#           }
#         }
#     '''
#     session = get_authorized_session(host)
#     response = session.post(admin_api_url, json={'query': query})

#     failover = response.json()['data']['cluster']['failover']

#     assert failover == configured_failover


# def test_auth_params(host):
#     # Get configured auth params
#     configured_auth = host.ansible.get_variables()['cartridge_auth']

#     # Get all configured instances
#     configured_instances = get_configured_instances()

#     if not configured_instances:
#         return

#     # Select one instance to be control
#     admin_api_url = get_admin_api_url(configured_instances)

#     # Get cluster auth params
#     query = '''
#         query {
#             cluster {
#                 auth_params {
#                     enabled
#                     cookie_max_age
#                     cookie_renew_age
#                 }
#             }
#         }
#     '''

#     session = get_authorized_session(host)
#     response = session.post(admin_api_url, json={'query': query})

#     auth = response.json()['data']['cluster']['auth_params']

#     for key in ['enabled', 'cookie_max_age', 'cookie_renew_age']:
#         if key in configured_auth:
#             assert auth[key] == configured_auth[key]


# def test_auth_users(host):
#     # Get configured auth params
#     ansible_vars = host.ansible.get_variables()
#     if 'cartridge_auth' not in ansible_vars:
#         return

#     configured_auth = ansible_vars['cartridge_auth']

#     if 'users' not in configured_auth:
#         return

#     # Get all configured instances
#     configured_instances = get_configured_instances()

#     if not configured_instances:
#         return

#     # Select one instance to be control
#     admin_api_url = get_admin_api_url(configured_instances)

#     # Get cluster auth params
#     query = '''
#         query {
#             cluster {
#                 users {
#                     username
#                     fullname
#                     email
#                 }
#             }
#         }
#     '''

#     session = get_authorized_session(host)
#     response = session.post(admin_api_url, json={'query': query})

#     auth_users = response.json()['data']['cluster']['users']
#     auth_users = {
#         u['username']: u for u in auth_users
#         if u['username'] != 'admin' and not user_is_deleted(u)
#     }
#     configured_users = {u['username']: u for u in configured_auth['users']}

#     assert auth_users.keys() == configured_users.keys()
#     for k in auth_users.keys():
#         conf_user = configured_users[k]
#         user = auth_users[k]

#         for p in ['fullname', 'email']:
#             if p in conf_user:
#                 assert user[p] == conf_user[p]

#     # Check if all users can log in
#     login_url = 'http://{}:{}/login'.format(
#         'localhost',
#         configured_instances[0]['http_port']
#     )

#     for username, user in configured_users.items():
#         if 'password' not in user:
#             continue

#         response = requests.post(login_url, json={'username': username, 'password': user['password']})
#         assert response.status_code == 200


# def test_app_config(host):
#     # Get configured auth params
#     ansible_vars = host.ansible.get_variables()
#     if 'cartridge_app_config' not in ansible_vars:
#         return

#     specified_app_config = ansible_vars['cartridge_app_config']

#     # Get all configured instances
#     configured_instances = get_configured_instances()

#     if not configured_instances:
#         return

#     # Get cartridge app config
#     config_url = 'http://{}:{}/admin/config'.format(
#         'localhost',
#         configured_instances[0]['http_port']
#     )

#     session = get_authorized_session(host)

#     response = session.get(config_url)
#     assert response.status_code == 200
#     app_config = yaml.safe_load(response.content)

#     # Check if app config is equal to configured one
#     for section_name, section in specified_app_config.items():
#         if section_is_deleted(section):
#             assert section_name not in app_config
#         else:
#             assert section_name in app_config
#             assert app_config[section_name] == section['body']
