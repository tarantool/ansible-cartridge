# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest
from instance import Instance

from helpers import set_box_cfg

from library.cartridge_instance import manage_instance


def call_manage_instance(control_sock,
                         config={},
                         cartridge_defaults={}):
    return manage_instance({
        'control_sock': control_sock,
        'config': config,
        'cartridge_defaults': cartridge_defaults,
    })


class TestManageInstance(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_instance_not_started(self):
        # console sock doesn't exists
        self.instance.clear_calls('box_cfg')
        self.instance.remove_file(self.console_sock)

        res = call_manage_instance(
            control_sock=self.console_sock
        )

        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)
        self.assertEqual(len(self.instance.get_calls('box_cfg')), 0)

        # cennot connect to console sock
        self.instance.clear_calls('box_cfg')
        bad_socket_path = 'bad-socket-path'
        self.instance.write_file(bad_socket_path)

        res = call_manage_instance(
            control_sock=bad_socket_path
        )

        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)
        self.assertEqual(len(self.instance.get_calls('box_cfg')), 0)

        # memtx_memory is nil
        self.instance.clear_calls('box_cfg')
        set_box_cfg(self.instance, memtx_memory=None)

        res = call_manage_instance(
            control_sock=self.console_sock
        )

        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)
        self.assertEqual(len(self.instance.get_calls('box_cfg')), 0)

    def test_memtx_memory_decreasing(self):
        BIG_MEMTX_MEMORY = 1024
        SMALL_MEMTX_MEMORY = 512

        self.instance.clear_calls('box_cfg')
        set_box_cfg(self.instance, memtx_memory=BIG_MEMTX_MEMORY)

        res = call_manage_instance(
            control_sock=self.console_sock,
            config={
                'memtx_memory': SMALL_MEMTX_MEMORY,
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        self.assertEqual(len(self.instance.get_calls('box_cfg')), 0)

    def test_memtx_memory_increasing(self):
        SMALL_MEMTX_MEMORY = 512
        INSTANCE_BIG_MEMTX_MEMORY = 1024
        APP_BIG_MEMTX_MEMORY = 2048

        # increased only in instance config
        self.instance.clear_calls('box_cfg')
        set_box_cfg(self.instance, memtx_memory=SMALL_MEMTX_MEMORY)

        res = call_manage_instance(
            control_sock=self.console_sock,
            config={
                'memtx_memory': INSTANCE_BIG_MEMTX_MEMORY,
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({'memtx_memory': INSTANCE_BIG_MEMTX_MEMORY}, calls)

        # increased only in app config
        self.instance.clear_calls('box_cfg')
        set_box_cfg(self.instance, memtx_memory=SMALL_MEMTX_MEMORY)

        res = call_manage_instance(
            control_sock=self.console_sock,
            cartridge_defaults={
                'memtx_memory': APP_BIG_MEMTX_MEMORY,
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({'memtx_memory': APP_BIG_MEMTX_MEMORY}, calls)

        # increased in both app and instace config
        self.instance.clear_calls('box_cfg')
        set_box_cfg(self.instance, memtx_memory=SMALL_MEMTX_MEMORY)

        res = call_manage_instance(
            control_sock=self.console_sock,
            config={
                'memtx_memory': INSTANCE_BIG_MEMTX_MEMORY,
            },
            cartridge_defaults={
                'memtx_memory': APP_BIG_MEMTX_MEMORY,
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({'memtx_memory': INSTANCE_BIG_MEMTX_MEMORY}, calls)

    def test_memtx_memory_increasing_fails(self):
        SMALL_MEMTX_MEMORY = 512
        INSTANCE_BIG_MEMTX_MEMORY = 1024
        APP_BIG_MEMTX_MEMORY = 2048

        self.instance.set_fail_on('increase_memtx_memory')

        # increased only in instance config
        self.instance.clear_calls('box_cfg')
        set_box_cfg(self.instance, memtx_memory=SMALL_MEMTX_MEMORY)

        res = call_manage_instance(
            control_sock=self.console_sock,
            config={
                'memtx_memory': INSTANCE_BIG_MEMTX_MEMORY,
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({'memtx_memory': INSTANCE_BIG_MEMTX_MEMORY}, calls)

        # increased only in app config
        self.instance.clear_calls('box_cfg')
        set_box_cfg(self.instance, memtx_memory=SMALL_MEMTX_MEMORY)

        res = call_manage_instance(
            control_sock=self.console_sock,
            cartridge_defaults={
                'memtx_memory': APP_BIG_MEMTX_MEMORY,
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({'memtx_memory': APP_BIG_MEMTX_MEMORY}, calls)

        # increased in both app and instace config
        self.instance.clear_calls('box_cfg')
        set_box_cfg(self.instance, memtx_memory=SMALL_MEMTX_MEMORY)

        res = call_manage_instance(
            control_sock=self.console_sock,
            config={
                'memtx_memory': INSTANCE_BIG_MEMTX_MEMORY,
            },
            cartridge_defaults={
                'memtx_memory': APP_BIG_MEMTX_MEMORY,
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 1)
        self.assertIn({'memtx_memory': INSTANCE_BIG_MEMTX_MEMORY}, calls)

    def test_box_cfg_is_function(self):
        BIG_MEMTX_MEMORY = 1024

        self.instance.clear_calls('box_cfg')
        self.instance.set_box_cfg_function()

        res = call_manage_instance(
            control_sock=self.console_sock,
            config={
                'memtx_memory': BIG_MEMTX_MEMORY,
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('box_cfg')
        self.assertEqual(len(calls), 0)

    def tearDown(self):
        self.instance.stop()
