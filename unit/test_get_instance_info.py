import sys
import unittest

import module_utils.helpers as helpers

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_get_instance_info import get_app_conf_file
from library.cartridge_get_instance_info import get_instance_conf_file
from library.cartridge_get_instance_info import get_instance_conf_section
from library.cartridge_get_instance_info import get_instance_info
from library.cartridge_get_instance_info import get_instance_systemd_service
from library.cartridge_get_instance_info import get_multiversion_dist_dir


def call_get_instance_info(app_name, instance_name, instance_vars):
    return get_instance_info({
        'app_name': app_name,
        'instance_name': instance_name,
        'instance_vars': instance_vars,
    })


class TestGetInstanceInfo(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_pid_file(self):
        pid_file = helpers.get_instance_pid_file('some/run/dir', 'myapp', 'instance-1')
        self.assertEqual(pid_file, 'some/run/dir/myapp.instance-1.pid')

        pid_file = helpers.get_instance_pid_file('some/run/dir', 'myapp', 'instance-1', stateboard=True)
        self.assertEqual(pid_file, 'some/run/dir/myapp-stateboard.pid')

    def test_console_sock(self):
        console_sock = helpers.get_instance_console_sock('some/run/dir', 'myapp', 'instance-1')
        self.assertEqual(console_sock, 'some/run/dir/myapp.instance-1.control')

        console_sock = helpers.get_instance_console_sock('some/run/dir', 'myapp', 'instance-1', stateboard=True)
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

    def test_get_instance_dir(self):
        instance_work_dir = helpers.get_instance_dir('some/data/dir', 'myapp', 'instance-1')
        self.assertEqual(instance_work_dir, 'some/data/dir/myapp.instance-1')

        instance_work_dir = helpers.get_instance_dir('some/data/dir', 'myapp', 'instance-1', stateboard=True)
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
            'cartridge_memtx_dir_parent': 'some/memtx/dir',
            'cartridge_vinyl_dir_parent': 'some/vinyl/dir',
            'cartridge_wal_dir_parent': 'some/wal/dir',
            'cartridge_app_install_dir': 'some/install/dir',
            'cartridge_app_instances_dir': 'some/instances/dir',
            'cartridge_tmpfiles_dir': '/some/tmpfiles/dir',
            'cartridge_multiversion': False,
            'stateboard': False,
        }

        res = call_get_instance_info(app_name, instance_name, instance_vars)
        self.assertFalse(res.failed)
        self.assertEqual(res.fact, {
            'app_conf_file': 'some/conf/dir/myapp.yml',
            'conf_file': 'some/conf/dir/myapp.instance-1.yml',
            'instance_id': 'myapp.instance-1',
            'console_sock': 'some/run/dir/myapp.instance-1.control',
            'pid_file': 'some/run/dir/myapp.instance-1.pid',
            'work_dir': 'some/data/dir/myapp.instance-1',
            'memtx_dir': 'some/memtx/dir/myapp.instance-1',
            'vinyl_dir': 'some/vinyl/dir/myapp.instance-1',
            'wal_dir': 'some/wal/dir/myapp.instance-1',
            'systemd_service': 'myapp@instance-1',
            'tmpfiles_conf': '/some/tmpfiles/dir/myapp.conf',
            'dist_dir': 'some/install/dir/myapp',
            'instance_dist_dir': 'some/install/dir/myapp',
            'paths_to_remove_on_expel': [
                'some/conf/dir/myapp.instance-1.yml',
                'some/data/dir/myapp.instance-1',
                'some/memtx/dir/myapp.instance-1',
                'some/run/dir/myapp.instance-1.control',
                'some/run/dir/myapp.instance-1.pid',
                'some/vinyl/dir/myapp.instance-1',
                'some/wal/dir/myapp.instance-1',
            ],
            'files_to_remove_on_cleanup': [
                'some/run/dir/myapp.instance-1.control',
                'some/run/dir/myapp.instance-1.pid',
            ],
            'dirs_to_remove_on_cleanup': [
                'some/data/dir/myapp.instance-1',
                'some/memtx/dir/myapp.instance-1',
                'some/vinyl/dir/myapp.instance-1',
                'some/wal/dir/myapp.instance-1',
            ],
        })

    def test_get_instance_info_multiversion(self):
        app_name = 'myapp'
        instance_name = 'instance-1'
        instance_vars = {
            'cartridge_package_path': 'myapp-0.1.0-1.rpm',
            'cartridge_conf_dir': 'some/conf/dir',
            'cartridge_run_dir': 'some/run/dir',
            'cartridge_data_dir': 'some/data/dir',
            'cartridge_memtx_dir_parent': None,
            'cartridge_vinyl_dir_parent': None,
            'cartridge_wal_dir_parent': None,
            'cartridge_app_install_dir': 'some/install/dir',
            'cartridge_app_instances_dir': 'some/instances/dir',
            'cartridge_tmpfiles_dir': '/some/tmpfiles/dir',
            'cartridge_multiversion': True,
            'stateboard': False,
        }

        res = call_get_instance_info(app_name, instance_name, instance_vars)
        self.assertFalse(res.failed)
        self.assertEqual(res.fact, {
            'app_conf_file': 'some/conf/dir/myapp.yml',
            'conf_file': 'some/conf/dir/myapp.instance-1.yml',
            'instance_id': 'myapp.instance-1',
            'console_sock': 'some/run/dir/myapp.instance-1.control',
            'pid_file': 'some/run/dir/myapp.instance-1.pid',
            'work_dir': 'some/data/dir/myapp.instance-1',
            'memtx_dir': None,
            'vinyl_dir': None,
            'wal_dir': None,
            'systemd_service': 'myapp@instance-1',
            'tmpfiles_conf': '/some/tmpfiles/dir/myapp.conf',
            'dist_dir': 'some/install/dir/myapp-0.1.0-1',
            'instance_dist_dir': 'some/instances/dir/myapp.instance-1',
            'paths_to_remove_on_expel': [
                'some/conf/dir/myapp.instance-1.yml',
                'some/data/dir/myapp.instance-1',
                'some/run/dir/myapp.instance-1.control',
                'some/run/dir/myapp.instance-1.pid',
            ],
            'files_to_remove_on_cleanup': [
                'some/run/dir/myapp.instance-1.control',
                'some/run/dir/myapp.instance-1.pid',
            ],
            'dirs_to_remove_on_cleanup': [
                'some/data/dir/myapp.instance-1',
            ],
        })

        # cartridge_package_path isn't specified
        instance_vars = {
            'cartridge_conf_dir': 'some/conf/dir',
            'cartridge_run_dir': 'some/run/dir',
            'cartridge_data_dir': 'some/data/dir',
            'cartridge_memtx_dir_parent': None,
            'cartridge_vinyl_dir_parent': None,
            'cartridge_wal_dir_parent': None,
            'cartridge_app_install_dir': 'some/install/dir',
            'cartridge_app_instances_dir': 'some/instances/dir',
            'cartridge_tmpfiles_dir': '/some/tmpfiles/dir',
            'cartridge_multiversion': True,
            'stateboard': False,
        }

        res = call_get_instance_info(app_name, instance_name, instance_vars)
        self.assertFalse(res.failed)
        self.assertEqual(res.fact, {
            'app_conf_file': 'some/conf/dir/myapp.yml',
            'conf_file': 'some/conf/dir/myapp.instance-1.yml',
            'instance_id': 'myapp.instance-1',
            'console_sock': 'some/run/dir/myapp.instance-1.control',
            'pid_file': 'some/run/dir/myapp.instance-1.pid',
            'work_dir': 'some/data/dir/myapp.instance-1',
            'memtx_dir': None,
            'vinyl_dir': None,
            'wal_dir': None,
            'systemd_service': 'myapp@instance-1',
            'tmpfiles_conf': '/some/tmpfiles/dir/myapp.conf',
            'dist_dir': None,
            'instance_dist_dir': 'some/instances/dir/myapp.instance-1',
            'paths_to_remove_on_expel': [
                'some/conf/dir/myapp.instance-1.yml',
                'some/data/dir/myapp.instance-1',
                'some/run/dir/myapp.instance-1.control',
                'some/run/dir/myapp.instance-1.pid',
            ],
            'files_to_remove_on_cleanup': [
                'some/run/dir/myapp.instance-1.control',
                'some/run/dir/myapp.instance-1.pid',
            ],
            'dirs_to_remove_on_cleanup': [
                'some/data/dir/myapp.instance-1',
            ],
        })

    def test_get_stateboard_info(self):
        app_name = 'myapp'
        instance_name = 'instance-1'
        instance_vars = {
            'cartridge_package_path': 'myapp-0.1.0-1.rpm',
            'cartridge_conf_dir': 'some/conf/dir',
            'cartridge_run_dir': 'some/run/dir',
            'cartridge_data_dir': 'some/data/dir',
            'cartridge_memtx_dir_parent': None,
            'cartridge_vinyl_dir_parent': None,
            'cartridge_wal_dir_parent': None,
            'cartridge_app_install_dir': 'some/install/dir',
            'cartridge_app_instances_dir': 'some/instances/dir',
            'cartridge_tmpfiles_dir': '/some/tmpfiles/dir',
            'cartridge_multiversion': False,
            'stateboard': True,
        }

        res = call_get_instance_info(app_name, instance_name, instance_vars)
        self.assertFalse(res.failed)
        self.assertEqual(res.fact, {
            'app_conf_file': 'some/conf/dir/myapp.yml',
            'conf_file': 'some/conf/dir/myapp-stateboard.yml',
            'instance_id': 'myapp-stateboard',
            'console_sock': 'some/run/dir/myapp-stateboard.control',
            'pid_file': 'some/run/dir/myapp-stateboard.pid',
            'work_dir': 'some/data/dir/myapp-stateboard',
            'memtx_dir': None,
            'vinyl_dir': None,
            'wal_dir': None,
            'systemd_service': 'myapp-stateboard',
            'tmpfiles_conf': '/some/tmpfiles/dir/myapp.conf',
            'dist_dir': 'some/install/dir/myapp',
            'instance_dist_dir': 'some/install/dir/myapp',
            'paths_to_remove_on_expel': [
                'some/conf/dir/myapp-stateboard.yml',
                'some/data/dir/myapp-stateboard',
                'some/run/dir/myapp-stateboard.control',
                'some/run/dir/myapp-stateboard.pid',
            ],
            'files_to_remove_on_cleanup': [
                'some/run/dir/myapp-stateboard.control',
                'some/run/dir/myapp-stateboard.pid',
            ],
            'dirs_to_remove_on_cleanup': [
                'some/data/dir/myapp-stateboard',
            ],
        })

    def test_get_stateboard_info_multiversion(self):
        app_name = 'myapp'
        instance_name = 'instance-1'
        instance_vars = {
            'cartridge_package_path': 'myapp-0.1.0-1.rpm',
            'cartridge_conf_dir': 'some/conf/dir',
            'cartridge_run_dir': 'some/run/dir',
            'cartridge_data_dir': 'some/data/dir',
            'cartridge_memtx_dir_parent': 'some/memtx/dir',
            'cartridge_vinyl_dir_parent': 'some/vinyl/dir',
            'cartridge_wal_dir_parent': 'some/wal/dir',
            'cartridge_app_install_dir': 'some/install/dir',
            'cartridge_app_instances_dir': 'some/instances/dir',
            'cartridge_tmpfiles_dir': '/some/tmpfiles/dir',
            'cartridge_multiversion': True,
            'stateboard': True,
        }

        res = call_get_instance_info(app_name, instance_name, instance_vars)
        self.assertFalse(res.failed)
        self.assertEqual(res.fact, {
            'app_conf_file': 'some/conf/dir/myapp.yml',
            'conf_file': 'some/conf/dir/myapp-stateboard.yml',
            'instance_id': 'myapp-stateboard',
            'console_sock': 'some/run/dir/myapp-stateboard.control',
            'pid_file': 'some/run/dir/myapp-stateboard.pid',
            'work_dir': 'some/data/dir/myapp-stateboard',
            'memtx_dir': 'some/memtx/dir/myapp-stateboard',
            'vinyl_dir': 'some/vinyl/dir/myapp-stateboard',
            'wal_dir': 'some/wal/dir/myapp-stateboard',
            'systemd_service': 'myapp-stateboard',
            'tmpfiles_conf': '/some/tmpfiles/dir/myapp.conf',
            'dist_dir': 'some/install/dir/myapp-0.1.0-1',
            'instance_dist_dir': 'some/instances/dir/myapp-stateboard',
            'paths_to_remove_on_expel': [
                'some/conf/dir/myapp-stateboard.yml',
                'some/data/dir/myapp-stateboard',
                'some/memtx/dir/myapp-stateboard',
                'some/run/dir/myapp-stateboard.control',
                'some/run/dir/myapp-stateboard.pid',
                'some/vinyl/dir/myapp-stateboard',
                'some/wal/dir/myapp-stateboard',
            ],
            'files_to_remove_on_cleanup': [
                'some/run/dir/myapp-stateboard.control',
                'some/run/dir/myapp-stateboard.pid',
            ],
            'dirs_to_remove_on_cleanup': [
                'some/data/dir/myapp-stateboard',
                'some/memtx/dir/myapp-stateboard',
                'some/vinyl/dir/myapp-stateboard',
                'some/wal/dir/myapp-stateboard',
            ],
        })
