import sys
import unittest

from parameterized import parameterized

import module_utils.helpers as helpers
from unit.instance import Instance

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_patch_instance_in_runtime import patch_instance_in_runtime


def call_configure_instance(console_sock, instance_config=None, cartridge_defaults=None, strict_mode=False):
    return patch_instance_in_runtime({
        'console_sock': console_sock,
        'instance_config': instance_config or {},
        'cartridge_defaults': cartridge_defaults or {},
        'strict_mode': strict_mode,
    })


class TestManageInstance(unittest.TestCase):
    def setUp(self):
        self.instance = Instance()
        self.console_sock = self.instance.console_sock
        self.cookie = self.instance.cluster_cookie

        self.instance.start()

    def test_instance_not_running(self):
        # console sock doesn't exists
        self.instance.clear_calls('box_cfg')
        self.instance.remove_file(self.console_sock)

        res = call_configure_instance(
            console_sock=self.console_sock
        )

        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)
        self.assertEqual(len(self.instance.get_calls('box_cfg')), 0)

        # cannot connect to console sock
        self.instance.clear_calls('box_cfg')
        bad_socket_path = 'bad-socket-path'
        self.instance.write_file(bad_socket_path)

        res = call_configure_instance(
            console_sock=bad_socket_path
        )

        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)
        self.assertEqual(len(self.instance.get_calls('box_cfg')), 0)

        # memtx_memory is nil
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(memtx_memory=None)

        res = call_configure_instance(
            console_sock=self.console_sock
        )

        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)
        self.assertEqual(len(self.instance.get_calls('box_cfg')), 0)

    def test_non_dynamic_params(self):
        param_name = 'advertise_uri'
        old_value = 'localhost:3301'
        new_instance_value = 'localhost:3311'
        new_app_value = 'localhost:3322'

        # changed only in instance config
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: old_value})

        res = call_configure_instance(
            console_sock=self.console_sock,
            instance_config={
                param_name: new_instance_value,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 0)

        # changed only in app config
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: old_value})

        res = call_configure_instance(
            console_sock=self.console_sock,
            cartridge_defaults={
                param_name: new_app_value,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 0)

        # changed in both app and instance config
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: old_value})

        res = call_configure_instance(
            console_sock=self.console_sock,
            instance_config={
                param_name: new_instance_value,
            },
            cartridge_defaults={
                param_name: new_app_value,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 0)

        # changed only in instance config with strict mode
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: old_value})

        res = call_configure_instance(
            console_sock=self.console_sock,
            instance_config={
                param_name: new_instance_value,
            },
            strict_mode=True,
        )
        self.assertTrue(res.failed)
        self.assertEqual(res.msg,
                         "Impossible to patch instance config: impossible to change '%s' in runtime" % param_name)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 0)

        # changed only in app config with strict mode
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: old_value})

        res = call_configure_instance(
            console_sock=self.console_sock,
            cartridge_defaults={
                param_name: new_app_value,
            },
            strict_mode=True,
        )
        self.assertTrue(res.failed)
        self.assertEqual(res.msg,
                         "Impossible to patch instance config: impossible to change '%s' in runtime" % param_name)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 0)

    @parameterized.expand([
        ["memtx_memory"],
        ["vinyl_memory"],
    ])
    def test_memory_decreasing(self, param_name):
        BIG_MEMORY = 1024
        SMALL_MEMORY = 512

        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: BIG_MEMORY})

        res = call_configure_instance(
            console_sock=self.console_sock,
            instance_config={
                param_name: SMALL_MEMORY,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        self.assertEqual(len(self.instance.get_calls('box_cfg')), 0)

        res = call_configure_instance(
            console_sock=self.console_sock,
            instance_config={
                param_name: SMALL_MEMORY,
            },
            strict_mode=True,
        )
        self.assertTrue(res.failed)
        self.assertEqual(
            res.msg,
            "Impossible to patch instance config: "
            "impossible to decrease memory sizes in runtime ('%s' from '%s' to '%s')" % (
                param_name, BIG_MEMORY, SMALL_MEMORY,
            ),
        )

        self.assertEqual(len(self.instance.get_calls('box_cfg')), 0)

    @parameterized.expand([
        ["memtx_memory"],
        ["vinyl_memory"],
    ])
    def test_memtx_memory_increasing(self, param_name):
        SMALL_MEMORY = 512
        INSTANCE_BIG_MEMORY = 1024
        APP_BIG_MEMORY = 2048

        # increased only in instance config
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: SMALL_MEMORY})

        res = call_configure_instance(
            console_sock=self.console_sock,
            instance_config={
                param_name: INSTANCE_BIG_MEMORY,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({param_name: INSTANCE_BIG_MEMORY}, calls)

        # increased only in app config
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: SMALL_MEMORY})

        res = call_configure_instance(
            console_sock=self.console_sock,
            cartridge_defaults={
                param_name: APP_BIG_MEMORY,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({param_name: APP_BIG_MEMORY}, calls)

        # increased in both app and instance config
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: SMALL_MEMORY})

        res = call_configure_instance(
            console_sock=self.console_sock,
            instance_config={
                param_name: INSTANCE_BIG_MEMORY,
            },
            cartridge_defaults={
                param_name: APP_BIG_MEMORY,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({param_name: INSTANCE_BIG_MEMORY}, calls)

    @parameterized.expand([
        ["memtx_memory"],
        ["vinyl_memory"],
    ])
    def test_memtx_memory_increasing_fails(self, param_name):
        SMALL_MEMORY = 512
        INSTANCE_BIG_MEMORY = 1024
        APP_BIG_MEMORY = 2048

        self.instance.set_fail_on('increase_memory_size')

        # increased only in instance config
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: SMALL_MEMORY})

        res = call_configure_instance(
            console_sock=self.console_sock,
            instance_config={
                param_name: INSTANCE_BIG_MEMORY,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({param_name: INSTANCE_BIG_MEMORY}, calls)

        # increased only in app config
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: SMALL_MEMORY})

        res = call_configure_instance(
            console_sock=self.console_sock,
            cartridge_defaults={
                param_name: APP_BIG_MEMORY,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({param_name: APP_BIG_MEMORY}, calls)

        # increased in both app and instance config
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: SMALL_MEMORY})

        res = call_configure_instance(
            console_sock=self.console_sock,
            instance_config={
                param_name: INSTANCE_BIG_MEMORY,
            },
            cartridge_defaults={
                param_name: APP_BIG_MEMORY,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({param_name: INSTANCE_BIG_MEMORY}, calls)

    def test_box_cfg_is_function(self):
        BIG_MEMTX_MEMORY = 1024

        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg_function()

        res = call_configure_instance(
            console_sock=self.console_sock,
            instance_config={
                'memtx_memory': BIG_MEMTX_MEMORY,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 0)

    # test non-dynamic param changed

    @parameterized.expand([
        ['string', 'custom_proc_title', 'old-proc-title', 'new-proc-title', 'new-app-proc-title'],
        ['number', 'checkpoint_interval', 3600, 1800, 900],
        ['boolean', 'read_only', False, True, True],
    ])
    def test_dynamic_params(self, _, param_name, old_value, new_instance_value, new_app_value):
        # changed only in instance config
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: old_value})

        res = call_configure_instance(
            console_sock=self.console_sock,
            instance_config={
                param_name: new_instance_value,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({param_name: new_instance_value}, calls)

        # changed only in app config
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: old_value})

        res = call_configure_instance(
            console_sock=self.console_sock,
            cartridge_defaults={
                param_name: new_app_value,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({param_name: new_app_value}, calls)

        # changed in both app and instance config
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: old_value})

        res = call_configure_instance(
            console_sock=self.console_sock,
            instance_config={
                param_name: new_instance_value,
            },
            cartridge_defaults={
                param_name: new_app_value,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({param_name: new_instance_value}, calls)

        # specified in instance config, isn't changed
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: old_value})

        res = call_configure_instance(
            console_sock=self.console_sock,
            instance_config={
                param_name: old_value,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 0)

        # specified in app config, isn't changed
        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg(**{param_name: old_value})

        res = call_configure_instance(
            console_sock=self.console_sock,
            cartridge_defaults={
                param_name: old_value,
            }
        )
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 0)

    def tearDown(self):
        self.instance.stop()
        del self.instance
