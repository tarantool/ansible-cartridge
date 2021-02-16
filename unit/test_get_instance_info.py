# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import unittest

from library.cartridge_get_instance_info import get_instance_info
from library.cartridge_get_instance_info import get_instance_pid_file
from library.cartridge_get_instance_info import get_instance_conf_file
from library.cartridge_get_instance_info import get_app_conf_file
from library.cartridge_get_instance_info import get_instance_conf_section
from library.cartridge_get_instance_info import get_instance_work_dir
from library.cartridge_get_instance_info import get_instance_systemd_service
from library.cartridge_get_instance_info import get_package_type

from ansible.module_utils.helpers import get_instance_console_sock


def call_get_instance_info(app_name, instance_name, instance_vars):
    return get_instance_info({
        'app_name': app_name,
        'instance_name': instance_name,
        'instance_vars': instance_vars,
    })


class TestGetInstanceInfo(unittest.TestCase):
    def test_pid_file(self):
        pid_file = get_instance_pid_file('some/run/dir', 'myapp', 'instance-1')
        self.assertEqual(pid_file, 'some/run/dir/myapp.instance-1.pid')

        pid_file = get_instance_pid_file('some/run/dir', 'myapp', 'instance-1', stateboard=True)
        self.assertEqual(pid_file, 'some/run/dir/myapp-stateboard.pid')

    def test_console_sock(self):
        console_sock = get_instance_console_sock('some/run/dir', 'myapp', 'instance-1')
        self.assertEqual(console_sock, 'some/run/dir/myapp.instance-1.control')

        console_sock = get_instance_console_sock('some/run/dir', 'myapp', 'instance-1', stateboard=True)
        self.assertEqual(console_sock, 'some/run/dir/myapp-stateboard.control')

    def test_get_instance_conf_file(self):
        conf_file = get_instance_conf_file('some/conf/dir', 'myapp', 'instance-1')
        self.assertEqual(conf_file, 'some/conf/dir/myapp.instance-1.yml')

        conf_file = get_instance_conf_file('some/conf/dir', 'myapp', 'instance-1', stateboard=True)
        self.assertEqual(conf_file, 'some/conf/dir/myapp-stateboard.yml')

    def test_get_app_conf_file(self):
        app_conf_file = get_app_conf_file('some/conf/dir', 'myapp')
        self.assertEqual(app_conf_file, 'some/conf/dir/myapp.yml')

    def test_get_instance_conf_section(self):
        instance_conf_section = get_instance_conf_section('myapp', 'instance-1')
        self.assertEqual(instance_conf_section, 'myapp.instance-1')

        instance_conf_section = get_instance_conf_section('myapp', 'instance-1', stateboard=True)
        self.assertEqual(instance_conf_section, 'myapp-stateboard')

    def test_get_instance_work_dir(self):
        instance_work_dir = get_instance_work_dir('some/data/dir', 'myapp', 'instance-1')
        self.assertEqual(instance_work_dir, 'some/data/dir/myapp.instance-1')

        instance_work_dir = get_instance_work_dir('some/data/dir', 'myapp', 'instance-1', stateboard=True)
        self.assertEqual(instance_work_dir, 'some/data/dir/myapp-stateboard')

    def test_get_instance_systemd_service(self):
        instance_systemd_service = get_instance_systemd_service('myapp', 'instance-1')
        self.assertEqual(instance_systemd_service, 'myapp@instance-1')

        instance_systemd_service = get_instance_systemd_service('myapp', 'instance-1', stateboard=True)
        self.assertEqual(instance_systemd_service, 'myapp-stateboard')

    def test_get_package_type(self):
        self.assertEqual(get_package_type('some-package.rpm'), 'rpm')
        self.assertEqual(get_package_type('some-package.deb'), 'deb')
        self.assertEqual(get_package_type('some-package.tar.gz'), 'tgz')
        self.assertEqual(get_package_type(None), None)

        with self.assertRaises(Exception) as ctx:
            get_package_type('some-package.zip')

        self.assertIn('Package of unsupported type is specified', str(ctx.exception))

    def test_get_instance_info(self):
        app_name = 'myapp'
        instance_name = 'instance-1'
        instance_vars = {
            'cartridge_package_path': 'some-package.rpm',
            'cartridge_conf_dir': 'some/conf/dir',
            'cartridge_run_dir': 'some/run/dir',
            'cartridge_data_dir': 'some/data/dir',
            'cartridge_dist_dir': 'some/dist/dir',
            'stateboard': False,
        }

        res = call_get_instance_info(app_name, instance_name, instance_vars)
        self.assertTrue(res.success)
        self.assertEqual(res.meta, {
            'package_type': 'rpm',
            'instance_code_dir': 'some/dist/dir/myapp',
            'app_conf_file': 'some/conf/dir/myapp.yml',
            'conf_file': 'some/conf/dir/myapp.instance-1.yml',
            'conf_section': 'myapp.instance-1',
            'console_sock': 'some/run/dir/myapp.instance-1.control',
            'pid_file': 'some/run/dir/myapp.instance-1.pid',
            'work_dir': 'some/data/dir/myapp.instance-1',
            'systemd_service': 'myapp@instance-1',
        })

    def test_get_stateboard_info(self):
        app_name = 'myapp'
        instance_name = 'instance-1'
        instance_vars = {
            'cartridge_package_path': 'some-package.rpm',
            'cartridge_conf_dir': 'some/conf/dir',
            'cartridge_run_dir': 'some/run/dir',
            'cartridge_data_dir': 'some/data/dir',
            'cartridge_dist_dir': 'some/dist/dir',
            'stateboard': True,
        }

        res = call_get_instance_info(app_name, instance_name, instance_vars)
        self.assertTrue(res.success)
        self.assertEqual(res.meta, {
            'package_type': 'rpm',
            'instance_code_dir': 'some/dist/dir/myapp',
            'app_conf_file': 'some/conf/dir/myapp.yml',
            'conf_file': 'some/conf/dir/myapp-stateboard.yml',
            'conf_section': 'myapp-stateboard',
            'console_sock': 'some/run/dir/myapp-stateboard.control',
            'pid_file': 'some/run/dir/myapp-stateboard.pid',
            'work_dir': 'some/data/dir/myapp-stateboard',
            'systemd_service': 'myapp-stateboard',
        })
