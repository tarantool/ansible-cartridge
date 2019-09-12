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


def check_conf_file(conf_file, conf_section, conf):
    assert conf_file.exists
    assert conf_file.user == 'tarantool'
    assert conf_file.group == 'tarantool'

    conf_file_dict = yaml.load(conf_file.content_string, Loader=yaml.FullLoader)

    assert conf_section in conf_file_dict
    assert conf_file_dict[conf_section] == conf


def get_instance_alias(instance):
    return instance['alias'] if 'alias' in instance else instance['name']


def test_instances_status_and_config(host):
    ansible_vars = host.ansible.get_variables()
    instances = copy.deepcopy(ansible_vars['cartridge_config']['instances'])
    default_conf = ansible_vars['cartridge_config_defaults']

    for instance in instances:
        inst_name = instance['name']

        # Remove deploy params from instance conf
        deploy_params = ['name', 'roles', 'replica_for']
        for p in deploy_params:
            if p in instance:
                del instance[p]

        service = host.service('{}@{}'.format(APP_NAME, inst_name))
        assert service.is_running

        conf_file_path = '/etc/tarantool/conf.d/{}.{}.yml'.format(APP_NAME, inst_name)
        conf_file = host.file(conf_file_path)
        conf_section = '{}.{}'.format(APP_NAME, inst_name)

        check_conf_file(conf_file, conf_section, instance)

    default_conf_file_path = '/etc/tarantool/conf.d/{}.yml'.format(APP_NAME)
    default_conf_file = host.file(default_conf_file_path)
    default_conf_file_section = APP_NAME

    check_conf_file(default_conf_file, default_conf_file_section, default_conf)


def test_replicasets(host):
    # Get all configured instances
    configured_instances = []

    for host in testinfra_hosts:
        configured_instances += ansible_runner.get_variables(host)['cartridge_config']['instances']

    if not configured_instances:
        return

    # Select one instance to be control
    control_instance = configured_instances[0]
    control_instance_admin_api_url = 'http://{}:{}/admin/api'.format(
        'localhost',  # Works while docker ports are exposed
        control_instance['http_port']
    )

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
    response = requests.post(control_instance_admin_api_url, json={'query': query})

    started_instances = response.json()['data']['servers']
    started_instances = {i['alias']: i for i in started_instances}

    # Check if all configyred instances are started and avaliable
    assert len(configured_instances) == len(started_instances)
    for configured_instance in configured_instances:
        assert get_instance_alias(configured_instance) in started_instances

    # Collect configured replicasets
    configured_replicasets = {
        get_instance_alias(configured_instance): {
            'replicas': [],
            'roles': configured_instance['roles']
        }
        for configured_instance in configured_instances if 'roles' in configured_instance
    }

    for configured_instance in configured_instances:
        if 'replica_for' in configured_instance:
            instance_alias = get_instance_alias(configured_instance)
            configured_replicasets[configured_instance['replica_for']]['replicas'].append(instance_alias)

    # Get started replicasets
    query = '''
        query {
          replicasets {
            uuid
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
    response = requests.post(control_instance_admin_api_url, json={'query': query})
    started_replicasets = response.json()['data']['replicasets']

    # Check if started replicasets are equal to configured
    for started_replicaset in started_replicasets:
        master_alias = started_replicaset['master']['alias']

        assert master_alias in configured_replicasets
        configured_replicaset = configured_replicasets[master_alias]

        started_replicaset_servers = [s['alias'] for s in started_replicaset['servers']]
        assert set(started_replicaset_servers) == set(configured_replicaset['replicas'] + [master_alias])
        assert set(started_replicaset['roles']) == set(configured_replicaset['roles'])
