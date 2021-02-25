import itertools
import unittest

from parameterized import parameterized

from helpers import set_box_cfg
from instance import Instance
from library.cartridge_set_needs_restart import needs_restart


def call_needs_restart(console_sock,
                       app_name=Instance.APP_NAME,
                       instance_conf_file=Instance.INSTANCE_CONF_PATH,
                       app_conf_file=Instance.APP_CONF_PATH,
                       instance_dist_dir=Instance.APP_CODE_PATH,
                       instance_id=Instance.instance_id,
                       config=None,
                       cluster_cookie=Instance.COOKIE,
                       cartridge_defaults=None,
                       stateboard=False):
    instance_info = {
        'console_sock': console_sock,
        'app_conf_file': app_conf_file,
        'conf_file': instance_conf_file,
        'instance_id': instance_id,
        'instance_dist_dir': instance_dist_dir,
    }

    return needs_restart({
        'app_name': app_name,
        'config': config or {},
        'cartridge_defaults': cartridge_defaults or {},
        'cluster_cookie': cluster_cookie,
        'stateboard': stateboard,
        'instance_info': instance_info,
    })


class TestSetNeedsRestart(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_instance_not_started(self):
        # console sock doesn't exists
        self.instance.remove_file(self.console_sock)

        res = call_needs_restart(
            console_sock=self.console_sock
        )

        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)
        self.assertIsNotNone(res.facts)
        self.assertTrue('needs_restart' in res.facts and res.facts['needs_restart'] is True)

        # cannot connect to console sock
        bad_socket_path = 'bad-socket-path'
        self.instance.write_file(bad_socket_path)

        res = call_needs_restart(
            console_sock=bad_socket_path
        )

        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)
        self.assertIsNotNone(res.facts)
        self.assertTrue('needs_restart' in res.facts and res.facts['needs_restart'] is True)

    def test_box_cfg_is_function(self):
        param_name = 'some-param'
        old_value = 'old-value'
        new_value = 'new-value'

        self.instance.set_box_cfg_function()

        self.instance.set_instance_config({
            param_name: old_value,
        })

        # nothing changed
        res = call_needs_restart(
            console_sock=self.console_sock,
            config={
                param_name: old_value,
            },
        )

        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)
        self.assertIsNotNone(res.facts)
        self.assertTrue('needs_restart' in res.facts and res.facts['needs_restart'] is True)

        # param was changed
        res = call_needs_restart(
            console_sock=self.console_sock,
            config={
                param_name: new_value,
            },
        )

        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)
        self.assertIsNotNone(res.facts)
        self.assertTrue('needs_restart' in res.facts and res.facts['needs_restart'] is True)

    def test_code_was_updated(self):
        # code was updated today, socket yesterday - needs restart
        self.instance.set_path_m_time(self.instance.APP_CODE_PATH, self.instance.DATE_TODAY)
        self.instance.set_path_m_time(self.console_sock, self.instance.DATE_YESTERDAY)

        res = call_needs_restart(console_sock=self.console_sock)

        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)
        self.assertIsNotNone(res.facts)
        self.assertTrue('needs_restart' in res.facts and res.facts['needs_restart'] is True)

    @parameterized.expand(
        itertools.product(
            ["instance", "stateboard"],
            ["memtx_memory", "vinyl_memory"],
        )
    )
    def test_config_changed(self, instance_type, memory_param_name):
        param_name = 'param'
        param_current_value = 'current-value'
        param_new_value = 'new-value'

        current_memory_size = 100
        memtx_memory_new_value = 200

        stateboard = instance_type == 'stateboard'

        self.instance.set_instance_config({
            param_name: param_current_value,
            memory_param_name: current_memory_size
        })
        set_box_cfg(self.instance, **{memory_param_name: current_memory_size})

        # nothing changed
        res = call_needs_restart(
            console_sock=self.console_sock,
            config={
                param_name: param_current_value,
                memory_param_name: current_memory_size
            },
            stateboard=stateboard,
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)
        facts = res.facts or {}
        self.assertTrue('needs_restart' not in facts or facts['needs_restart'] is False)

        # param changed, memory size not
        res = call_needs_restart(
            console_sock=self.console_sock,
            config={
                param_name: param_new_value,
                memory_param_name: current_memory_size
            },
            stateboard=stateboard
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)
        self.assertIsNotNone(res.facts)
        self.assertTrue('needs_restart' in res.facts and res.facts['needs_restart'] is True)

        # param isn't changed
        # memory size is changed in config
        # but isn't changed on instance
        set_box_cfg(self.instance, **{memory_param_name: current_memory_size})
        res = call_needs_restart(
            console_sock=self.console_sock,
            config={
                param_name: param_current_value,
                memory_param_name: memtx_memory_new_value
            },
            stateboard=stateboard
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)
        self.assertIsNotNone(res.facts)
        self.assertTrue('needs_restart' in res.facts and res.facts['needs_restart'] is True)

        # param isn't changed
        # memory size is changed in config
        # and changed on instance
        set_box_cfg(self.instance, **{memory_param_name: memtx_memory_new_value})
        res = call_needs_restart(
            console_sock=self.console_sock,
            config={
                param_name: param_current_value,
                memory_param_name: memtx_memory_new_value
            },
            stateboard=stateboard
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)
        facts = res.facts or {}
        self.assertTrue('needs_restart' not in facts or facts['needs_restart'] is False)

        # param is changed
        # memory size is changed in config
        # and changed on instance
        set_box_cfg(self.instance, **{memory_param_name: memtx_memory_new_value})
        res = call_needs_restart(
            console_sock=self.console_sock,
            config={
                param_name: param_new_value,
                memory_param_name: memtx_memory_new_value
            },
            stateboard=stateboard
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)
        self.assertIsNotNone(res.facts)
        self.assertTrue('needs_restart' in res.facts and res.facts['needs_restart'] is True)

    @parameterized.expand(
        itertools.product(
            ["instance", "stateboard"],
            ["memtx_memory", "vinyl_memory"],
        )
    )
    def test_app_config_changed(self, instance_type, memory_param_name):
        param_name = 'param'
        param_current_value = 'current-value'
        param_new_value = 'new-value'

        current_memory_size = 100
        memtx_memory_new_value = 200

        stateboard = instance_type == 'stateboard'

        self.instance.set_app_config({
            param_name: param_current_value,
            memory_param_name: current_memory_size
        })
        set_box_cfg(self.instance, **{memory_param_name: current_memory_size})

        # nothing changed
        res = call_needs_restart(
            console_sock=self.console_sock,
            cartridge_defaults={
                param_name: param_current_value,
                memory_param_name: current_memory_size
            },
            stateboard=stateboard
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)
        facts = res.facts or {}
        self.assertTrue('needs_restart' not in facts or facts['needs_restart'] is False)

        # param changed, memory size not
        res = call_needs_restart(
            console_sock=self.console_sock,
            cartridge_defaults={
                param_name: param_new_value,
                memory_param_name: current_memory_size
            },
            stateboard=stateboard
        )
        self.assertFalse(res.failed, msg=res.msg)
        if not stateboard:
            self.assertTrue(res.changed)
            self.assertIsNotNone(res.facts)
            self.assertTrue('needs_restart' in res.facts and res.facts['needs_restart'] is True)
        else:
            self.assertFalse(res.changed)
            facts = res.facts or {}
            self.assertTrue('needs_restart' not in facts or facts['needs_restart'] is False)

        # param isn't changed
        # memory size is changed in config
        # but isn't changed on instance
        set_box_cfg(self.instance, **{memory_param_name: current_memory_size})
        res = call_needs_restart(
            console_sock=self.console_sock,
            cartridge_defaults={
                param_name: param_current_value,
                memory_param_name: memtx_memory_new_value
            },
            stateboard=stateboard
        )
        self.assertFalse(res.failed, msg=res.msg)
        if not stateboard:
            self.assertTrue(res.changed)
            self.assertIsNotNone(res.facts)
            self.assertTrue('needs_restart' in res.facts and res.facts['needs_restart'] is True)
        else:
            self.assertFalse(res.changed)
            facts = res.facts or {}
            self.assertTrue('needs_restart' not in facts or facts['needs_restart'] is False)

        # param isn't changed
        # memory size is changed in config
        # and changed on instance
        set_box_cfg(self.instance, **{memory_param_name: memtx_memory_new_value})
        res = call_needs_restart(
            console_sock=self.console_sock,
            cartridge_defaults={
                param_name: param_current_value,
                memory_param_name: memtx_memory_new_value
            },
            stateboard=stateboard
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)
        facts = res.facts or {}
        self.assertTrue('needs_restart' not in facts or facts['needs_restart'] is False)

        # param is changed
        # memory size is changed in config
        # and changed on instance
        set_box_cfg(self.instance, **{memory_param_name: memtx_memory_new_value})
        res = call_needs_restart(
            console_sock=self.console_sock,
            cartridge_defaults={
                param_name: param_new_value,
                memory_param_name: memtx_memory_new_value
            },
            stateboard=stateboard
        )
        self.assertFalse(res.failed, msg=res.msg)
        if not stateboard:
            self.assertTrue(res.changed)
            self.assertIsNotNone(res.facts)
            self.assertTrue('needs_restart' in res.facts and res.facts['needs_restart'] is True)
        else:
            self.assertFalse(res.changed)
            facts = res.facts or {}
            self.assertTrue('needs_restart' not in facts or facts['needs_restart'] is False)

    @parameterized.expand([
        ["memtx_memory"],
        ["vinyl_memory"],
    ])
    def test_memory_size_changed(self, memory_param_name):
        current_memory_size = 100
        new_memory_size_instance = 200
        new_memory_size_app = 300

        self.instance.set_app_config({
            memory_param_name: current_memory_size
        })
        self.instance.set_instance_config({
            memory_param_name: current_memory_size
        })
        set_box_cfg(self.instance, **{memory_param_name: current_memory_size})

        # nothing changed
        res = call_needs_restart(
            console_sock=self.console_sock,
            config={
                memory_param_name: current_memory_size
            },
            cartridge_defaults={
                memory_param_name: current_memory_size
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)
        facts = res.facts or {}
        self.assertTrue('needs_restart' not in facts or facts['needs_restart'] is False)

        # memory size changed only in cartridge_defaults
        res = call_needs_restart(
            console_sock=self.console_sock,
            config={
                memory_param_name: current_memory_size
            },
            cartridge_defaults={
                memory_param_name: new_memory_size_instance
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)
        facts = res.facts or {}
        self.assertTrue('needs_restart' not in facts or facts['needs_restart'] is False)

        # memory size changed both in cartridge_defaults and config
        res = call_needs_restart(
            console_sock=self.console_sock,
            config={
                memory_param_name: new_memory_size_instance
            },
            cartridge_defaults={
                memory_param_name: new_memory_size_app
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)
        self.assertIsNotNone(res.facts)
        self.assertTrue('needs_restart' in res.facts and res.facts['needs_restart'] is True)

        # memory size changed both in cartridge_defaults and config
        # memory size on instance is equal to value from cartridge_defaults
        set_box_cfg(self.instance, **{memory_param_name: new_memory_size_app})
        res = call_needs_restart(
            console_sock=self.console_sock,
            config={
                memory_param_name: new_memory_size_instance
            },
            cartridge_defaults={
                memory_param_name: new_memory_size_app
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)
        self.assertIsNotNone(res.facts)
        self.assertTrue('needs_restart' in res.facts and res.facts['needs_restart'] is True)

        # memory size changed both in cartridge_defaults and config
        # memory size on instance is equal to value from config
        set_box_cfg(self.instance, **{memory_param_name: new_memory_size_instance})
        res = call_needs_restart(
            console_sock=self.console_sock,
            config={
                memory_param_name: new_memory_size_instance
            },
            cartridge_defaults={
                memory_param_name: new_memory_size_app
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)
        facts = res.facts or {}
        self.assertTrue('needs_restart' not in facts or facts['needs_restart'] is False)

    def tearDown(self):
        self.instance.stop()
        del self.instance
