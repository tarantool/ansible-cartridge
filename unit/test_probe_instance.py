# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest
from instance import Instance

from library.cartridge_probe_instance import probe_server


def call_probe_instance(control_sock, hostvars, play_hosts=None):
    if play_hosts is None:
        play_hosts = hostvars.keys()

    return probe_server({
        'control_sock': control_sock,
        'hostvars': hostvars,
        'play_hosts': play_hosts,
    })


def set_known_servers(instance, servers):
    instance.set_variable('known_servers', {
        s: True for s in servers
    })


URI1 = '127.0.0.1:3301'
URI2 = '127.0.0.1:3302'


class TestProbeInstance(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_probe_ok(self):
        set_known_servers(self.instance, [URI1, URI2])

        # one instance
        self.instance.clear_calls('admin_probe_server')
        res = call_probe_instance(
            control_sock=self.console_sock,
            hostvars={
                'instance-1': {
                    'config': {'advertise_uri': URI1},
                }
            }
        )
        self.assertTrue(res.success, msg=res.msg)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertEqual(len(calls), 1)
        self.assertIn(URI1, calls)

        # two instances
        self.instance.clear_calls('admin_probe_server')
        res = call_probe_instance(
            control_sock=self.console_sock,
            hostvars={
                'instance-1': {
                    'config': {'advertise_uri': URI1},
                },
                'instance-2': {
                    'config': {'advertise_uri': URI2},
                }
            }
        )
        self.assertTrue(res.success, msg=res.msg)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertEqual(len(calls), 2)
        self.assertIn(URI1, calls)
        self.assertIn(URI2, calls)

    def test_probe_one_fails(self):
        set_known_servers(self.instance, [URI1])

        # probe not known server
        self.instance.clear_calls('admin_probe_server')
        res = call_probe_instance(
            control_sock=self.console_sock,
            hostvars={
                'instance-2': {
                    'config': {'advertise_uri': URI2},
                }
            }
        )
        self.assertFalse(res.success)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertEqual(len(calls), 1)
        self.assertIn(URI2, calls)

        # probe both known and not known server
        self.instance.clear_calls('admin_probe_server')
        res = call_probe_instance(
            control_sock=self.console_sock,
            hostvars={
                'instance-1': {
                    'config': {'advertise_uri': URI1},
                },
                'instance-2': {
                    'config': {'advertise_uri': URI2},
                }
            }
        )
        self.assertFalse(res.success)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertIn(len(calls), [1, 2])
        if len(calls) == 1:
            self.assertIn(URI2, calls)
        else:
            self.assertIn(URI1, calls)
            self.assertIn(URI2, calls)

    def test_probe_expelled(self):
        # expelled server shouldn't be probed
        set_known_servers(self.instance, [URI1])

        # probe only expelled
        self.instance.clear_calls('admin_probe_server')
        res = call_probe_instance(
            control_sock=self.console_sock,
            hostvars={
                'instance-2': {
                    'expelled': True,
                    'config': {'advertise_uri': URI2},
                }
            }
        )
        self.assertTrue(res.success, msg=res.msg)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertEqual(len(calls), 0)

        # probe both expelled and not
        self.instance.clear_calls('admin_probe_server')
        res = call_probe_instance(
            control_sock=self.console_sock,
            hostvars={
                'instance-1': {
                    'config': {'advertise_uri': URI1},
                },
                'instance-2': {
                    'expelled': True,
                    'config': {'advertise_uri': URI2},
                }
            }
        )
        self.assertTrue(res.success, msg=res.msg)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertEqual(len(calls), 1)
        self.assertIn(URI1, calls)

    def test_probe_restarted(self):
        # restarted server should be probed
        set_known_servers(self.instance, [])

        self.instance.clear_calls('admin_probe_server')
        res = call_probe_instance(
            control_sock=self.console_sock,
            hostvars={
                'instance-2': {
                    'restarted': True,
                    'config': {'advertise_uri': URI2},
                }
            }
        )
        self.assertFalse(res.success)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertEqual(len(calls), 1)
        self.assertIn(URI2, calls)

    def test_failed_for_non_play_host(self):
        set_known_servers(self.instance, [URI1])

        # probe can fail for instance not mentioned in play_hosts
        # but it should be probed
        self.instance.clear_calls('admin_probe_server')

        res = call_probe_instance(
            control_sock=self.console_sock,
            hostvars={
                'instance-1': {
                    'config': {'advertise_uri': URI1},
                },
                'instance-2': {
                    'config': {'advertise_uri': URI2},
                }
            },
            play_hosts=['instance-1']
        )
        self.assertTrue(res.success, msg=res.msg)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertEqual(len(calls), 2)
        self.assertIn(URI1, calls)
        self.assertIn(URI2, calls)

    def tearDown(self):
        self.instance.stop()
