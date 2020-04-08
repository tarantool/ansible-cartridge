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


URI1 = '127.0.0.1:3301'
URI2 = '127.0.0.1:3302'


class TestProbeInstance(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_probe_ok(self):
        self.instance.set_cartridge_known_server(URI1, True)
        self.instance.set_cartridge_known_server(URI2, True)

        self.instance.clear_probed(URI1)
        res = call_probe_instance(
            control_sock=self.console_sock,
            hostvars={
                'instance-1': {
                    'config': {'advertise_uri': URI1},
                }
            }
        )
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(self.instance.server_was_probed(URI1))

        self.instance.clear_probed(URI1)
        self.instance.clear_probed(URI2)
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
        self.assertTrue(self.instance.server_was_probed(URI1))
        self.assertTrue(self.instance.server_was_probed(URI2))

    def test_probe_one_fails(self):
        self.instance.set_cartridge_known_server(URI1, True)
        self.instance.set_cartridge_known_server(URI2, False)

        self.instance.clear_probed(URI2)
        res = call_probe_instance(
            control_sock=self.console_sock,
            hostvars={
                'instance-2': {
                    'config': {'advertise_uri': URI2},
                }
            }
        )
        self.assertFalse(res.success)
        self.assertTrue(self.instance.server_was_probed(URI2))

        self.instance.clear_probed(URI1)
        self.instance.clear_probed(URI2)
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
        self.assertTrue(self.instance.server_was_probed(URI1))
        self.assertTrue(self.instance.server_was_probed(URI2))

    def test_probe_expelled(self):
        # expelled server shouldn't be probed
        self.instance.set_cartridge_known_server(URI1, True)
        self.instance.set_cartridge_known_server(URI2, False)

        self.instance.clear_probed(URI2)
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
        self.assertFalse(self.instance.server_was_probed(URI2))

        self.instance.clear_probed(URI1)
        self.instance.clear_probed(URI2)
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
        self.assertTrue(self.instance.server_was_probed(URI1))
        self.assertFalse(self.instance.server_was_probed(URI2))

    def test_probe_restarted(self):
        # restarted server should be probed
        self.instance.set_cartridge_known_server(URI1, True)
        self.instance.set_cartridge_known_server(URI2, False)

        self.instance.clear_probed(URI2)
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
        self.assertTrue(self.instance.server_was_probed(URI2))

    def test_failed_for_non_play_host(self):
        self.instance.set_cartridge_known_server(URI1, True)
        self.instance.set_cartridge_known_server(URI2, False)

        # probe can fail for instance not mentioned in play_hosts
        # but it should be probed
        self.instance.clear_probed(URI1)
        self.instance.clear_probed(URI2)
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
        self.assertTrue(self.instance.server_was_probed(URI1))
        self.assertTrue(self.instance.server_was_probed(URI2))

    def tearDown(self):
        self.instance.stop()
