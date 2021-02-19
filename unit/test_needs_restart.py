import itertools
import unittest

from parameterized import parameterized

from helpers import set_box_cfg
from instance import Instance
from library.cartridge_needs_restart import needs_restart


def call_needs_restart(console_sock,
                       restarted=None,
                       app_name=Instance.APP_NAME,
                       instance_conf_file=Instance.INSTANCE_CONF_PATH,
                       app_conf_file=Instance.APP_CONF_PATH,
                       instance_code_dir=Instance.APP_CODE_PATH,
                       conf_section=Instance.CONF_SECTION,
                       config=None,
                       cluster_cookie=Instance.COOKIE,
                       cartridge_defaults=None,
                       stateboard=False):
    instance_info = {
        'console_sock': console_sock,
        'app_conf_file': app_conf_file,
        'conf_file': instance_conf_file,
        'conf_section': conf_section,
        'instance_code_dir': instance_code_dir,
    }

    return needs_restart({
        'app_name': app_name,
        'config': config or {},
        'cartridge_defaults': cartridge_defaults or {},
        'cluster_cookie': cluster_cookie,
        'restarted': restarted,
        'stateboard': stateboard,
        'instance_info': instance_info,
    })


class TestNeedsRestart(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_restart_forced(self):
        res = call_needs_restart(
            console_sock=self.console_sock,
            restarted=True
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

    def test_restart_disabled(self):
        res = call_needs_restart(
            console_sock=self.console_sock,
            restarted=False
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

    def test_instance_not_started(self):
        # console sock doesn't exists
        self.instance.remove_file(self.console_sock)

        res = call_needs_restart(
            console_sock=self.console_sock
        )

        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        # cannot connect to console sock
        bad_socket_path = 'bad-socket-path'
        self.instance.write_file(bad_socket_path)

        res = call_needs_restart(
            console_sock=bad_socket_path
        )

        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

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

        # param was changed
        res = call_needs_restart(
            console_sock=self.console_sock,
            config={
                param_name: new_value,
            },
        )

        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

    def test_code_was_updated(self):
        # code was updated today, socket yesterday - needs restart
        self.instance.set_path_m_time(self.instance.APP_CODE_PATH, self.instance.DATE_TODAY)
        self.instance.set_path_m_time(self.console_sock, self.instance.DATE_YESTERDAY)

        res = call_needs_restart(console_sock=self.console_sock)

        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

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
        else:
            self.assertFalse(res.changed)

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
        else:
            self.assertFalse(res.changed)

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
        else:
            self.assertFalse(res.changed)

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

    def tearDown(self):
        self.instance.stop()
        del self.instance
