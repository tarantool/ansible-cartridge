import os

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
HOSTS_PATH = os.path.join('molecule', 'update_cartridge', 'hosts.yml')

inventory = InventoryManager(loader=DataLoader(), sources=HOSTS_PATH)
variable_manager = VariableManager(loader=DataLoader(), inventory=inventory)

cluster_cookie = inventory.groups['cluster'].get_vars()['cartridge_cluster_cookie']

__authorized_session = None
__configured_instances = None


def get_authorized_session(cluster_cookie):
    global __authorized_session
    if __authorized_session is None:
        __authorized_session = requests.Session()
        __authorized_session.auth = ('admin', cluster_cookie)

    return __authorized_session


def get_configured_instances():
    global __configured_instances
    if __configured_instances is None:
        __configured_instances = {
            inventory.hosts[i].get_vars()['inventory_hostname']: inventory.hosts[i].get_vars()
            for i in inventory.hosts
        }
    return __configured_instances


def get_any_instance_http_port(instances):
    for _, instance_vars in instances.items():
        return instance_vars['config']['http_port']
    assert False


def get_admin_api_url(instances):
    admin_url = 'http://localhost:{}'.format(get_any_instance_http_port(instances))
    admin_api_url = '{}/admin/api'.format(
        admin_url
    )

    return admin_api_url


def test_cluster_is_healthy():
    configured_instances = get_configured_instances()

    # Select one instance to be control
    admin_api_url = get_admin_api_url(configured_instances)

    # Get all started instances
    query = '''
        query {
          replicasets {
            status
          }
        }
    '''
    session = get_authorized_session(cluster_cookie)
    response = session.post(admin_api_url, json={'query': query})
    assert response.status_code == 200

    replicasets = response.json()['data']['replicasets']
    assert all([r['status'] == 'healthy' for r in replicasets])
