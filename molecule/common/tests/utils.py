import os
import requests

import testinfra.utils.ansible_runner
from ansible.inventory.manager import InventoryManager
from ansible.vars.manager import VariableManager
from ansible.parsing.dataloader import DataLoader

scenario_name = os.environ['MOLECULE_SCENARIO_NAME']

DEFAULT_APP_NAME = 'myapp'

__inventory = None
__variable_manager = None
__cluster_vars = None
__cluster_cookie = None
__authorized_session = None
__configured_instances = None


def get_testinfra_hosts():
    ansible_runner = testinfra.utils.ansible_runner.AnsibleRunner(
        os.environ['MOLECULE_INVENTORY_FILE']
    )
    return ansible_runner.get_hosts('all')


def get_inventory():
    global __inventory
    if __inventory is None:
        HOSTS_PATH = os.path.join('molecule', scenario_name, 'hosts.yml')
        __inventory = InventoryManager(loader=DataLoader(), sources=HOSTS_PATH)

    return __inventory


def get_variable_manager():
    global __variable_manager
    if __variable_manager is None:
        inventory = get_inventory()
        __variable_manager = VariableManager(loader=DataLoader(), inventory=inventory)

    return __variable_manager


def get_cluster_vars():
    global __cluster_vars
    if __cluster_vars is None:
        inventory = get_inventory()
        __cluster_vars = inventory.groups['cluster'].get_vars()

    return __cluster_vars


def get_configured_instances():
    global __configured_instances
    if __configured_instances is None:
        inventory = get_inventory()
        __configured_instances = {
            inventory.hosts[i].get_vars()['inventory_hostname']: inventory.hosts[i].get_vars()
            for i in inventory.hosts
        }

    return __configured_instances


def get_instance_vars(instance):
    variable_manager = get_variable_manager()
    return variable_manager.get_vars(host=instance)


def get_cluster_var(name, default=None):
    cluster_vars = get_cluster_vars()
    return cluster_vars[name] if name in cluster_vars else default


def get_machine_instances(host):
    hostname = host.check_output('hostname -s')
    inventory = get_inventory()

    return [
        instance for instance in inventory.get_hosts()
        if get_instance_vars(instance).get('ansible_host') == hostname
    ]


def get_app_name():
    app_name = DEFAULT_APP_NAME
    if scenario_name == 'package_name':
        cluster_vars = get_cluster_vars()
        app_name = cluster_vars['cartridge_app_name']

    return app_name


def get_cluster_cookie():
    global __cluster_cookie
    if __cluster_cookie is None:
        __cluster_cookie = get_cluster_var('cartridge_cluster_cookie')

    return __cluster_cookie


def get_authorized_session():
    global __authorized_session
    if __authorized_session is None:
        cluster_cookie = get_cluster_cookie()
        __authorized_session = requests.Session()
        __authorized_session.auth = ('admin', cluster_cookie)

    return __authorized_session


def instance_is_expelled(host_vars):
    return 'expelled' in host_vars and host_vars['expelled'] is True


def instance_is_stateboard(host_vars):
    return host_vars.get('stateboard') is True


def get_any_instance_http_port():
    configured_instances = get_configured_instances()

    for _, instance_vars in configured_instances.items():
        if not instance_is_expelled(instance_vars) and not instance_is_stateboard(instance_vars):
            return instance_vars['config']['http_port']

    assert False


def get_any_instance_url():
    return 'http://localhost:%s' % get_any_instance_http_port()


def get_admin_api_url():
    return '%s/admin/api' % get_any_instance_url()
