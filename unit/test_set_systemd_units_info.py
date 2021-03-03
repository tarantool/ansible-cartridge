import unittest

from library.cartridge_set_systemd_units_info import get_systemd_units_info


def call_get_systemd_units_info(app_name, instance_vars, tnt_version):
    return get_systemd_units_info({
        'app_name': app_name,
        'instance_vars': instance_vars,
        'tnt_version': tnt_version,
    })


class TestSetInstanceInfo(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_multiversion_tnt_ce(self):
        app_name = 'myapp'
        tnt_version = '3.0'
        instance_vars = {
            'cartridge_multiversion': True,
            'cartridge_run_dir': 'some/run/dir',
            'cartridge_data_dir': 'some/data/dir',
            'dist_dir': '/some/dist/dir',
            'cartridge_app_instances_dir': 'some/instances/dir',
        }

        res = call_get_systemd_units_info(app_name, instance_vars, tnt_version)
        self.assertFalse(res.failed)
        self.assertEqual(res.facts, {'systemd_units_info': {
            'stateboard_name': 'myapp-stateboard',

            'app_unit_file': 'myapp@.service',
            'stateboard_unit_file': 'myapp-stateboard.service',

            'instance_work_dir': 'some/data/dir/myapp.%i',
            'stateboard_work_dir': 'some/data/dir/myapp-stateboard',

            'instance_pid_file': 'some/run/dir/myapp.%i.pid',
            'stateboard_pid_file': 'some/run/dir/myapp-stateboard.pid',
            'instance_console_sock': 'some/run/dir/myapp.%i.control',
            'stateboard_console_sock': 'some/run/dir/myapp-stateboard.control',

            'instance_entrypoint': 'some/instances/dir/myapp.%i/init.lua',
            'stateboard_entrypoint': 'some/instances/dir/myapp-stateboard/stateboard.init.lua',

            'instance_tarantool_binary': '/usr/bin/tarantool',
            'stateboard_tarantool_binary': '/usr/bin/tarantool',
        }})

    def test_multiversion_tnt_ee(self):
        app_name = 'myapp'
        tnt_version = ''
        instance_vars = {
            'cartridge_multiversion': True,
            'cartridge_run_dir': 'some/run/dir',
            'cartridge_data_dir': 'some/data/dir',
            'dist_dir': '/some/dist/dir',
            'cartridge_app_instances_dir': 'some/instances/dir',
        }

        res = call_get_systemd_units_info(app_name, instance_vars, tnt_version)
        self.assertFalse(res.failed)
        self.assertEqual(res.facts, {'systemd_units_info': {
            'stateboard_name': 'myapp-stateboard',

            'app_unit_file': 'myapp@.service',
            'stateboard_unit_file': 'myapp-stateboard.service',

            'instance_work_dir': 'some/data/dir/myapp.%i',
            'stateboard_work_dir': 'some/data/dir/myapp-stateboard',

            'instance_pid_file': 'some/run/dir/myapp.%i.pid',
            'stateboard_pid_file': 'some/run/dir/myapp-stateboard.pid',
            'instance_console_sock': 'some/run/dir/myapp.%i.control',
            'stateboard_console_sock': 'some/run/dir/myapp-stateboard.control',

            'instance_entrypoint': 'some/instances/dir/myapp.%i/init.lua',
            'stateboard_entrypoint': 'some/instances/dir/myapp-stateboard/stateboard.init.lua',

            'instance_tarantool_binary': 'some/instances/dir/myapp.%i/tarantool',
            'stateboard_tarantool_binary': 'some/instances/dir/myapp-stateboard/tarantool',
        }})

    def test_not_multiversion_tnt_ce(self):
        app_name = 'myapp'
        tnt_version = '3.0'
        instance_vars = {
            'cartridge_multiversion': False,
            'cartridge_run_dir': 'some/run/dir',
            'cartridge_data_dir': 'some/data/dir',
            'dist_dir': 'some/dist/dir',
            'cartridge_app_instances_dir': 'some/instances/dir',
        }

        res = call_get_systemd_units_info(app_name, instance_vars, tnt_version)
        self.assertFalse(res.failed)
        self.assertEqual(res.facts, {'systemd_units_info': {
            'stateboard_name': 'myapp-stateboard',

            'app_unit_file': 'myapp@.service',
            'stateboard_unit_file': 'myapp-stateboard.service',

            'instance_work_dir': 'some/data/dir/myapp.%i',
            'stateboard_work_dir': 'some/data/dir/myapp-stateboard',

            'instance_pid_file': 'some/run/dir/myapp.%i.pid',
            'stateboard_pid_file': 'some/run/dir/myapp-stateboard.pid',
            'instance_console_sock': 'some/run/dir/myapp.%i.control',
            'stateboard_console_sock': 'some/run/dir/myapp-stateboard.control',

            'instance_entrypoint': 'some/dist/dir/init.lua',
            'stateboard_entrypoint': 'some/dist/dir/stateboard.init.lua',

            'instance_tarantool_binary': '/usr/bin/tarantool',
            'stateboard_tarantool_binary': '/usr/bin/tarantool',
        }})

    def test_not_multiversion_tnt_ee(self):
        app_name = 'myapp'
        tnt_version = ''
        instance_vars = {
            'cartridge_multiversion': False,
            'cartridge_run_dir': 'some/run/dir',
            'cartridge_data_dir': 'some/data/dir',
            'dist_dir': 'some/dist/dir',
            'cartridge_app_instances_dir': 'some/instances/dir',
        }

        res = call_get_systemd_units_info(app_name, instance_vars, tnt_version)
        self.assertFalse(res.failed)
        self.assertEqual(res.facts, {'systemd_units_info': {
            'stateboard_name': 'myapp-stateboard',

            'app_unit_file': 'myapp@.service',
            'stateboard_unit_file': 'myapp-stateboard.service',

            'instance_work_dir': 'some/data/dir/myapp.%i',
            'stateboard_work_dir': 'some/data/dir/myapp-stateboard',

            'instance_pid_file': 'some/run/dir/myapp.%i.pid',
            'stateboard_pid_file': 'some/run/dir/myapp-stateboard.pid',
            'instance_console_sock': 'some/run/dir/myapp.%i.control',
            'stateboard_console_sock': 'some/run/dir/myapp-stateboard.control',

            'instance_entrypoint': 'some/dist/dir/init.lua',
            'stateboard_entrypoint': 'some/dist/dir/stateboard.init.lua',

            'instance_tarantool_binary': 'some/dist/dir/tarantool',
            'stateboard_tarantool_binary': 'some/dist/dir/tarantool',
        }})
