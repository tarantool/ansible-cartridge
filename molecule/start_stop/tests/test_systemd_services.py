import os

import testinfra.utils.ansible_runner

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


def test_services_status(host):
    hostname = host.check_output('hostname -s')

    machine_instances = [
        instance for instance in inventory.get_hosts()
        if variable_manager.get_vars(host=instance).get('ansible_host') == hostname
    ]

    assert machine_instances

    for instance in machine_instances:
        instance_vars = variable_manager.get_vars(host=instance)
        instance_name = instance_vars['inventory_hostname']

        service_name = '%s@%s' % (app_name, instance_name)
        service = host.service(service_name)

        running_instances = ['instance-started', 'instance-restarted', 'instance-restarted-force']
        if instance_name == 'instance-stopped':
            assert not service.is_running
            assert not service.is_enabled
        elif instance_name in running_instances:
            assert service.is_running
            assert service.is_enabled
        else:
            assert False
