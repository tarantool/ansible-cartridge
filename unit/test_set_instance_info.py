import unittest

from library.cartridge_set_instance_info import get_app_conf_file
from library.cartridge_set_instance_info import get_instance_conf_file
from library.cartridge_set_instance_info import get_instance_conf_section
from library.cartridge_set_instance_info import get_instance_info
from library.cartridge_set_instance_info import get_instance_systemd_service
from library.cartridge_set_instance_info import get_multiversion_dist_dir

from module_utils.helpers import get_instance_console_sock
from module_utils.helpers import get_instance_pid_file
from module_utils.helpers import get_instance_work_dir


def call_get_instance_info(app_name, instance_name, instance_vars):
    return get_instance_info({
        'app_name': app_name,
        'instance_name': instance_name,
        'instance_vars': instance_vars,
    })


class TestSetInstanceInfo(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

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

    def test_get_multiversion_app_code_dir(self):
        app_dir = get_multiversion_dist_dir('some/install/dir', 'myapp-0.1.0-1.rpm')
        self.assertEqual(app_dir, 'some/install/dir/myapp-0.1.0-1')
        app_dir = get_multiversion_dist_dir('some/install/dir', 'myapp-0.1.0-1-suffix.rpm')
        self.assertEqual(app_dir, 'some/install/dir/myapp-0.1.0-1-suffix')

        app_dir = get_multiversion_dist_dir('some/install/dir', 'myapp-0.1.0-1.deb')
        self.assertEqual(app_dir, 'some/install/dir/myapp-0.1.0-1')
        app_dir = get_multiversion_dist_dir('some/install/dir', 'myapp-0.1.0-1-suffix.deb')
        self.assertEqual(app_dir, 'some/install/dir/myapp-0.1.0-1-suffix')

        app_dir = get_multiversion_dist_dir('some/install/dir', 'myapp-0.1.0-1.tar.gz')
        self.assertEqual(app_dir, 'some/install/dir/myapp-0.1.0-1')
        app_dir = get_multiversion_dist_dir('some/install/dir', 'myapp-0.1.0-1-suffix.tar.gz')
        self.assertEqual(app_dir, 'some/install/dir/myapp-0.1.0-1-suffix')

    def test_get_instance_info(self):
        app_name = 'myapp'
        instance_name = 'instance-1'
        instance_vars = {
            'cartridge_package_path': 'myapp-0.1.0-1.rpm',
            'cartridge_conf_dir': 'some/conf/dir',
            'cartridge_run_dir': 'some/run/dir',
            'cartridge_data_dir': 'some/data/dir',
            'cartridge_install_dir': 'some/install/dir',
            'cartridge_instances_dir': 'some/instances/dir',
            'cartridge_tmpfiles_dir': '/some/tmpfiles/dir',
            'cartridge_multiversion': False,
            'stateboard': False,
        }

        res = call_get_instance_info(app_name, instance_name, instance_vars)
        self.assertFalse(res.failed)
        self.assertEqual(res.facts, {'instance_info': {
            'app_conf_file': 'some/conf/dir/myapp.yml',
            'conf_file': 'some/conf/dir/myapp.instance-1.yml',
            'instance_id': 'myapp.instance-1',
            'console_sock': 'some/run/dir/myapp.instance-1.control',
            'pid_file': 'some/run/dir/myapp.instance-1.pid',
            'work_dir': 'some/data/dir/myapp.instance-1',
            'systemd_service': 'myapp@instance-1',
            'tmpfiles_conf': '/some/tmpfiles/dir/myapp.conf',
            'dist_dir': 'some/install/dir/myapp',
            'instance_dist_dir': 'some/install/dir/myapp',
        }})

    def test_get_instance_info_multiversion(self):
        app_name = 'myapp'
        instance_name = 'instance-1'
        instance_vars = {
            'cartridge_package_path': 'myapp-0.1.0-1.rpm',
            'cartridge_conf_dir': 'some/conf/dir',
            'cartridge_run_dir': 'some/run/dir',
            'cartridge_data_dir': 'some/data/dir',
            'cartridge_install_dir': 'some/install/dir',
            'cartridge_instances_dir': 'some/instances/dir',
            'cartridge_tmpfiles_dir': '/some/tmpfiles/dir',
            'cartridge_multiversion': True,
            'stateboard': False,
        }

        res = call_get_instance_info(app_name, instance_name, instance_vars)
        self.assertFalse(res.failed)
        self.assertEqual(res.facts, {'instance_info': {
            'app_conf_file': 'some/conf/dir/myapp.yml',
            'conf_file': 'some/conf/dir/myapp.instance-1.yml',
            'instance_id': 'myapp.instance-1',
            'console_sock': 'some/run/dir/myapp.instance-1.control',
            'pid_file': 'some/run/dir/myapp.instance-1.pid',
            'work_dir': 'some/data/dir/myapp.instance-1',
            'systemd_service': 'myapp@instance-1',
            'tmpfiles_conf': '/some/tmpfiles/dir/myapp.conf',
            'dist_dir': 'some/install/dir/myapp-0.1.0-1',
            'instance_dist_dir': 'some/instances/dir/myapp.instance-1',
        }})

    def test_get_stateboard_info(self):
        app_name = 'myapp'
        instance_name = 'instance-1'
        instance_vars = {
            'cartridge_package_path': 'myapp-0.1.0-1.rpm',
            'cartridge_conf_dir': 'some/conf/dir',
            'cartridge_run_dir': 'some/run/dir',
            'cartridge_data_dir': 'some/data/dir',
            'cartridge_install_dir': 'some/install/dir',
            'cartridge_instances_dir': 'some/instances/dir',
            'cartridge_tmpfiles_dir': '/some/tmpfiles/dir',
            'cartridge_multiversion': False,
            'stateboard': True,
        }

        res = call_get_instance_info(app_name, instance_name, instance_vars)
        self.assertFalse(res.failed)
        self.assertEqual(res.facts, {'instance_info': {
            'app_conf_file': 'some/conf/dir/myapp.yml',
            'conf_file': 'some/conf/dir/myapp-stateboard.yml',
            'instance_id': 'myapp-stateboard',
            'console_sock': 'some/run/dir/myapp-stateboard.control',
            'pid_file': 'some/run/dir/myapp-stateboard.pid',
            'work_dir': 'some/data/dir/myapp-stateboard',
            'systemd_service': 'myapp-stateboard',
            'tmpfiles_conf': '/some/tmpfiles/dir/myapp.conf',
            'dist_dir': 'some/install/dir/myapp',
            'instance_dist_dir': 'some/install/dir/myapp',
        }})

    def test_get_stateboard_info_multiversion(self):
        app_name = 'myapp'
        instance_name = 'instance-1'
        instance_vars = {
            'cartridge_package_path': 'myapp-0.1.0-1.rpm',
            'cartridge_conf_dir': 'some/conf/dir',
            'cartridge_run_dir': 'some/run/dir',
            'cartridge_data_dir': 'some/data/dir',
            'cartridge_install_dir': 'some/install/dir',
            'cartridge_instances_dir': 'some/instances/dir',
            'cartridge_tmpfiles_dir': '/some/tmpfiles/dir',
            'cartridge_multiversion': True,
            'stateboard': True,
        }

        res = call_get_instance_info(app_name, instance_name, instance_vars)
        self.assertFalse(res.failed)
        self.assertEqual(res.facts, {'instance_info': {
            'app_conf_file': 'some/conf/dir/myapp.yml',
            'conf_file': 'some/conf/dir/myapp-stateboard.yml',
            'instance_id': 'myapp-stateboard',
            'console_sock': 'some/run/dir/myapp-stateboard.control',
            'pid_file': 'some/run/dir/myapp-stateboard.pid',
            'work_dir': 'some/data/dir/myapp-stateboard',
            'systemd_service': 'myapp-stateboard',
            'tmpfiles_conf': '/some/tmpfiles/dir/myapp.conf',
            'dist_dir': 'some/install/dir/myapp-0.1.0-1',
            'instance_dist_dir': 'some/instances/dir/myapp-stateboard',
        }})
