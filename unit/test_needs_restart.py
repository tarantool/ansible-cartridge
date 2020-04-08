# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest
from instance import Instance

from helpers import set_box_cfg

from library.cartridge_needs_restart import needs_restart


def call_needs_restart(control_sock,
                       restart_forced=False,
                       appname=Instance.APPNAME,
                       instance_name=Instance.INSTANCE_NAME,
                       config={},
                       cluster_cookie=Instance.COOKIE,
                       cartridge_defaults={}):
    return needs_restart({
        'restart_forced': restart_forced,
        'control_sock': control_sock,
        'appname': appname,
        'instance_name': instance_name,
        'cluster_cookie': cluster_cookie,
        'cartridge_defaults': cartridge_defaults,
        'config': config,
    })


class TestNeedsRestart(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_restart_forced(self):
        res = call_needs_restart(
            control_sock=self.console_sock,
            restart_forced=True
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

    def test_instance_not_started(self):
        # console sock doesn't exists
        self.instance.remove_file(self.console_sock)

        res = call_needs_restart(
            control_sock=self.console_sock
        )

        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        # cannot connect to console sock
        bad_socket_path = 'bad-socket-path'
        self.instance.write_file(bad_socket_path)

        res = call_needs_restart(
            control_sock=bad_socket_path
        )

        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

    def test_code_was_updated(self):
        # code was updated today, socket yesterday - needs restart
        self.instance.set_path_mtime(self.instance.APP_CODE_PATH, self.instance.DATE_TODAY)
        self.instance.set_path_mtime(self.console_sock, self.instance.DATE_YESTERDAY)

        res = call_needs_restart(
            control_sock=self.console_sock,
            instance_name=self.instance.INSTANCE_NAME
        )

        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

    def test_instance_config_changes(self):
        param_name = 'param'
        param_current_value = 'current-value'
        param_new_value = 'new-value'

        memtx_memory_param_name = 'memtx_memory'
        memtx_memory_current_value = 100
        memtx_memory_new_value = 200

        self.instance.set_instance_config({
            param_name: param_current_value,
            memtx_memory_param_name: memtx_memory_current_value
        })
        set_box_cfg(self.instance, memtx_memory=memtx_memory_current_value)

        # nothing changed
        res = call_needs_restart(
            control_sock=self.console_sock,
            config={
                param_name: param_current_value,
                memtx_memory_param_name: memtx_memory_current_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        # param changed, memtx_memory not
        res = call_needs_restart(
            control_sock=self.console_sock,
            config={
                param_name: param_new_value,
                memtx_memory_param_name: memtx_memory_current_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        # param isn't changed
        # memtx_memory is changed in config
        # but isn't changed on instance
        set_box_cfg(self.instance, memtx_memory=memtx_memory_current_value)
        res = call_needs_restart(
            control_sock=self.console_sock,
            config={
                param_name: param_current_value,
                memtx_memory_param_name: memtx_memory_new_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        # param isn't changed
        # memtx_memory is changed in config
        # and changed on instance
        set_box_cfg(self.instance, memtx_memory=memtx_memory_new_value)
        res = call_needs_restart(
            control_sock=self.console_sock,
            config={
                param_name: param_current_value,
                memtx_memory_param_name: memtx_memory_new_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        # param is changed
        # memtx_memory is changed in config
        # and changed on instance
        set_box_cfg(self.instance, memtx_memory=memtx_memory_new_value)
        res = call_needs_restart(
            control_sock=self.console_sock,
            config={
                param_name: param_new_value,
                memtx_memory_param_name: memtx_memory_new_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

    def test_app_config_changes(self):
        param_name = 'param'
        param_current_value = 'current-value'
        param_new_value = 'new-value'

        memtx_memory_param_name = 'memtx_memory'
        memtx_memory_current_value = 100
        memtx_memory_new_value = 200

        self.instance.set_app_config({
            param_name: param_current_value,
            memtx_memory_param_name: memtx_memory_current_value
        })
        set_box_cfg(self.instance, memtx_memory=memtx_memory_current_value)

        # nothing changed
        res = call_needs_restart(
            control_sock=self.console_sock,
            cartridge_defaults={
                param_name: param_current_value,
                memtx_memory_param_name: memtx_memory_current_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        # param changed, memtx_memory not
        res = call_needs_restart(
            control_sock=self.console_sock,
            cartridge_defaults={
                param_name: param_new_value,
                memtx_memory_param_name: memtx_memory_current_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        # param isn't changed
        # memtx_memory is changed in config
        # but isn't changed on instance
        set_box_cfg(self.instance, memtx_memory=memtx_memory_current_value)
        res = call_needs_restart(
            control_sock=self.console_sock,
            cartridge_defaults={
                param_name: param_current_value,
                memtx_memory_param_name: memtx_memory_new_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        # param isn't changed
        # memtx_memory is changed in config
        # and changed on instance
        set_box_cfg(self.instance, memtx_memory=memtx_memory_new_value)
        res = call_needs_restart(
            control_sock=self.console_sock,
            cartridge_defaults={
                param_name: param_current_value,
                memtx_memory_param_name: memtx_memory_new_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        # param is changed
        # memtx_memory is changed in config
        # and changed on instance
        set_box_cfg(self.instance, memtx_memory=memtx_memory_new_value)
        res = call_needs_restart(
            control_sock=self.console_sock,
            cartridge_defaults={
                param_name: param_new_value,
                memtx_memory_param_name: memtx_memory_new_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

    def test_both_app_and_instance_memtx_memory_changed(self):
        memtx_memory_param_name = 'memtx_memory'
        memtx_memory_current_value = 100
        memtx_memory_new_instance_value = 200
        memtx_memory_new_app_value = 300

        self.instance.set_app_config({
            memtx_memory_param_name: memtx_memory_current_value
        })
        self.instance.set_instance_config({
            memtx_memory_param_name: memtx_memory_current_value
        })
        set_box_cfg(self.instance, memtx_memory=memtx_memory_current_value)

        # nothing changed
        res = call_needs_restart(
            control_sock=self.console_sock,
            config={
                memtx_memory_param_name: memtx_memory_current_value
            },
            cartridge_defaults={
                memtx_memory_param_name: memtx_memory_current_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        # memtx_memory changed only in cartridge_defaults
        res = call_needs_restart(
            control_sock=self.console_sock,
            config={
                memtx_memory_param_name: memtx_memory_current_value
            },
            cartridge_defaults={
                memtx_memory_param_name: memtx_memory_new_instance_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        # memtx_memory changed both in cartridge_defaults and config
        res = call_needs_restart(
            control_sock=self.console_sock,
            config={
                memtx_memory_param_name: memtx_memory_new_instance_value
            },
            cartridge_defaults={
                memtx_memory_param_name: memtx_memory_new_app_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        # memtx_memory changed both in cartridge_defaults and config
        # memtx_memory on instance is equal to value from cartridge_defaults
        set_box_cfg(self.instance, memtx_memory=memtx_memory_new_app_value)
        res = call_needs_restart(
            control_sock=self.console_sock,
            config={
                memtx_memory_param_name: memtx_memory_new_instance_value
            },
            cartridge_defaults={
                memtx_memory_param_name: memtx_memory_new_app_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        # memtx_memory changed both in cartridge_defaults and config
        # memtx_memory on instance is equal to value from config
        set_box_cfg(self.instance, memtx_memory=memtx_memory_new_instance_value)
        res = call_needs_restart(
            control_sock=self.console_sock,
            config={
                memtx_memory_param_name: memtx_memory_new_instance_value
            },
            cartridge_defaults={
                memtx_memory_param_name: memtx_memory_new_app_value
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

    def tearDown(self):
        self.instance.stop()
