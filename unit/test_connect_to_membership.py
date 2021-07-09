import sys
import unittest

import module_utils.helpers as helpers
from unit.instance import Instance

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_connect_to_membership import connect_to_membership


def call_probe_instance(console_sock, module_hostvars, play_hosts=None, cluster_disabled_instances=None):
    if play_hosts is None:
        play_hosts = module_hostvars.keys()

    return connect_to_membership({
        'console_sock': console_sock,
        'module_hostvars': module_hostvars,
        'cluster_disabled_instances': cluster_disabled_instances or [],
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
        self.instance = Instance()
        self.console_sock = self.instance.console_sock
        self.cookie = self.instance.cluster_cookie

        self.instance.start()

    def test_probe_ok(self):
        set_known_servers(self.instance, [URI1, URI2])

        # one instance
        self.instance.clear_calls('admin_probe_server')
        res = call_probe_instance(
            console_sock=self.console_sock,
            module_hostvars={
                'instance-1': {
                    'config': {'advertise_uri': URI1},
                }
            }
        )
        self.assertFalse(res.failed, msg=res.msg)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertEqual(len(calls), 1)
        self.assertIn(URI1, calls)

        # two instances
        self.instance.clear_calls('admin_probe_server')
        res = call_probe_instance(
            console_sock=self.console_sock,
            module_hostvars={
                'instance-1': {
                    'config': {'advertise_uri': URI1},
                },
                'instance-2': {
                    'config': {'advertise_uri': URI2},
                }
            }
        )
        self.assertFalse(res.failed, msg=res.msg)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertEqual(len(calls), 2)
        self.assertIn(URI1, calls)
        self.assertIn(URI2, calls)

    def test_probe_one_fails(self):
        set_known_servers(self.instance, [URI1])

        # probe not known server
        self.instance.clear_calls('admin_probe_server')
        res = call_probe_instance(
            console_sock=self.console_sock,
            module_hostvars={
                'instance-2': {
                    'config': {'advertise_uri': URI2},
                }
            }
        )
        self.assertTrue(res.failed)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertEqual(len(calls), 1)
        self.assertIn(URI2, calls)

        # probe both known and not known server
        self.instance.clear_calls('admin_probe_server')
        res = call_probe_instance(
            console_sock=self.console_sock,
            module_hostvars={
                'instance-1': {
                    'config': {'advertise_uri': URI1},
                },
                'instance-2': {
                    'config': {'advertise_uri': URI2},
                }
            }
        )
        self.assertTrue(res.failed)

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
            console_sock=self.console_sock,
            module_hostvars={
                'instance-2': {
                    'expelled': True,
                    'config': {'advertise_uri': URI2},
                }
            }
        )
        self.assertFalse(res.failed, msg=res.msg)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertEqual(len(calls), 0)

        # probe both expelled and not
        self.instance.clear_calls('admin_probe_server')
        res = call_probe_instance(
            console_sock=self.console_sock,
            module_hostvars={
                'instance-1': {
                    'config': {'advertise_uri': URI1},
                },
                'instance-2': {
                    'expelled': True,
                    'config': {'advertise_uri': URI2},
                }
            }
        )
        self.assertFalse(res.failed, msg=res.msg)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertEqual(len(calls), 1)
        self.assertIn(URI1, calls)

    def test_probe_restarted(self):
        # restarted server should be probed
        set_known_servers(self.instance, [])

        self.instance.clear_calls('admin_probe_server')
        res = call_probe_instance(
            console_sock=self.console_sock,
            module_hostvars={
                'instance-2': {
                    'restarted': True,
                    'config': {'advertise_uri': URI2},
                }
            }
        )
        self.assertTrue(res.failed)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertEqual(len(calls), 1)
        self.assertIn(URI2, calls)

    def test_failed_for_non_play_host(self):
        set_known_servers(self.instance, [URI1])

        # probe can fail for instance not mentioned in play_hosts
        # but it should be probed
        self.instance.clear_calls('admin_probe_server')

        res = call_probe_instance(
            console_sock=self.console_sock,
            module_hostvars={
                'instance-1': {
                    'config': {'advertise_uri': URI1},
                },
                'instance-2': {
                    'config': {'advertise_uri': URI2},
                }
            },
            play_hosts=['instance-1']
        )
        self.assertFalse(res.failed, msg=res.msg)

        calls = self.instance.get_calls('admin_probe_server')
        self.assertEqual(len(calls), 2)
        self.assertIn(URI1, calls)
        self.assertIn(URI2, calls)

    def tearDown(self):
        self.instance.stop()
        del self.instance
