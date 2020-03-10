# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest
from instance import Instance

from library.cartridge_check_instance_started import check_instance_started


def call_check_instance_started(control_sock):
    return check_instance_started({
        'control_sock': control_sock,
    })


class TestInstanceStarted(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_alive(self):
        # require('membership').myself().status is 'active'
        self.instance.set_membership_status('alive')
        res = call_check_instance_started(self.console_sock)
        self.assertTrue(res.success)

        # require('membership').myself().status is 'dead'
        self.instance.set_membership_status('dead')
        res = call_check_instance_started(self.console_sock)
        self.assertFalse(res.success)

    def tearDown(self):
        self.instance.stop()
