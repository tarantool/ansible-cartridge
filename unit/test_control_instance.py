# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest
from instance import Instance

from library.cartridge_control_instance import get_control_instance


def call_get_control_instance(control_sock, allow_empty=True):
    return get_control_instance({
        'sock': control_sock,
        'allow_empty': allow_empty,
    })


URI1 = '127.0.0.1:3301'
URI2 = '127.0.0.1:3302'

UUID1 = 'uuid-1'
UUID2 = 'uuid-2'

ALIAS1 = 'alias-1'
ALIAS2 = 'alias-1'


def set_membership_members(instance, members):
    instance.set_variable('membership_members', {
        m['uri']: {
            'uri': m['uri'],
            'status': m.get('status', 'alive'),
            'incarnation': 1,
            'payload': {
                'uuid': m.get('uuid'),
                'alias': m.get('alias')
            }
        }
        for m in members
    })


class TestControlInstance(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_instance_without_alias(self):
        # with UUID (already bootstrapped) and without alias
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1},
        ])
        res = call_get_control_instance(self.console_sock)
        self.assertFalse(res.success)
        self.assertIn('Unable to get instance alias', res.msg)

    def test_one_instance(self):
        # with UUID and alias
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1, 'alias': ALIAS1},
        ])
        res = call_get_control_instance(self.console_sock)
        self.assertTrue(res.success, msg=res.msg)
        self.assertEqual(res.meta, {'host': ALIAS1})

        # without UUID
        set_membership_members(self.instance, [
            {'uri': URI1, 'alias': ALIAS1},
        ])
        res = call_get_control_instance(self.console_sock)
        self.assertTrue(res.success, msg=res.msg)
        self.assertEqual(res.meta, {'host': ''})

        # without UUID, allow_empty=False
        set_membership_members(self.instance, [
            {'uri': URI1, 'alias': ALIAS1},
        ])
        res = call_get_control_instance(self.console_sock, allow_empty=False)
        self.assertFalse(res.success)
        self.assertIn("Cluster isn't bootstrapped yet", res.msg)

    def test_two_instances(self):
        # both with UUID and alias (one is selected)
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1, 'alias': ALIAS1},
            {'uri': URI2, 'uuid': UUID2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(self.console_sock)
        self.assertTrue(res.success, msg=res.msg)
        self.assertIn(res.meta['host'], [ALIAS1, ALIAS2])

        # one with UUID (it is selected)
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1, 'alias': ALIAS1},
            {'uri': URI2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(self.console_sock)
        self.assertTrue(res.success, msg=res.msg)
        self.assertEqual(res.meta, {'host': ALIAS1})

        # one with UUID (but without alias)
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1},
            {'uri': URI2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(self.console_sock)
        self.assertFalse(res.success)
        self.assertIn("Unable to get instance alias", res.msg)

        # both without UUID (no one selected)
        set_membership_members(self.instance, [
            {'uri': URI1, 'alias': ALIAS1},
            {'uri': URI2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(self.console_sock)
        self.assertTrue(res.success, msg=res.msg)
        self.assertEqual(res.meta, {'host': ''})

        # both without UUID, allow_empty=False
        set_membership_members(self.instance, [
            {'uri': URI1, 'alias': ALIAS1},
            {'uri': URI2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(self.console_sock, allow_empty=False)
        self.assertFalse(res.success)
        self.assertIn("Cluster isn't bootstrapped yet", res.msg)

    def tearDown(self):
        self.instance.stop()
