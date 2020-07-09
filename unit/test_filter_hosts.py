import unittest
from filter_plugins.filter_hosts import FilterModule


class TestFilterHosts(unittest.TestCase):
    def setUp(self):
        self.filter_table = FilterModule().filters()

    def test_get_instance_control_sock_from_hostvars(self):
        instance_hostvars = {
            'control_sock_path': '/custom/sock/path.sock',
            'cartridge_app_name': 'app_name',
            'inventory_hostname': 'host_name'
        }
        self.assertEqual(
            self.filter_table['get_instance_control_sock'](instance_hostvars),
            instance_hostvars['control_sock_path']
        )

    def test_compose_instance_control_sock(self):
        instance_hostvars = {
            'cartridge_app_name': 'app_name',
            'inventory_hostname': 'host_name'
        }
        self.assertEqual(
            self.filter_table['get_instance_control_sock'](instance_hostvars),
            '/var/run/tarantool/{app_name}.{host_name}.control'.format(
                instance_hostvars['cartridge_app_name'],
                instance_hostvars['inventory_hostname']
            )
        )
