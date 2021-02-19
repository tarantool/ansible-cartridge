import unittest

from instance import Instance
from library.cartridge_set_control_instance import get_control_instance


def call_get_control_instance(console_sock, hostvars=None, play_hosts=None):
    if hostvars is None:
        hostvars = {}
    if play_hosts is None:
        play_hosts = hostvars.keys()

    return get_control_instance({
        'hostvars': hostvars,
        'play_hosts': play_hosts,
        'console_sock': console_sock,
    })


URI1 = '127.0.0.1:3301'
URI2 = '127.0.0.1:3302'

UUID1 = 'uuid-1'
UUID2 = 'uuid-2'

ALIAS1 = 'alias-1'
ALIAS2 = 'alias-2'

SOCK1 = '%s-sock-path' % ALIAS1
SOCK2 = '%s-sock-path' % ALIAS2


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


class TestSetControlInstance(unittest.TestCase):
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
        self.assertTrue(res.failed)
        self.assertIn('Unable to get instance alias', res.msg)

    def test_one_instance(self):
        hostvars = {
            ALIAS1: {
                'instance_info': {
                    'console_sock': SOCK1,
                },
            },
        }

        # with UUID and alias
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1, 'alias': ALIAS1},
        ])
        res = call_get_control_instance(self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.facts, {'control_instance': {
            'name': ALIAS1,
            'console_sock': SOCK1,
        }})

        # without UUID
        set_membership_members(self.instance, [
            {'uri': URI1, 'alias': ALIAS1},
        ])
        res = call_get_control_instance(self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn("Not found any joined instance or instance to create a replicaset", res.msg)

    def test_two_instances(self):
        hostvars = {
            ALIAS1: {
                'instance_info': {
                    'console_sock': SOCK1,
                },
            },
            ALIAS2: {
                'instance_info': {
                    'console_sock': SOCK2,
                },
            },
        }

        # both with UUID and alias (one is selected)
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1, 'alias': ALIAS1},
            {'uri': URI2, 'uuid': UUID2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertIn(res.facts['control_instance']['name'], [ALIAS1, ALIAS2])
        self.assertIn(res.facts['control_instance']['console_sock'], [SOCK1, SOCK2])

        # one with UUID (it is selected)
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1, 'alias': ALIAS1},
            {'uri': URI2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.facts, {'control_instance': {
            'name': ALIAS1,
            'console_sock': SOCK1,
        }})

        # one with UUID (but without alias)
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1},
            {'uri': URI2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn("Unable to get instance alias", res.msg)

        # both without UUID (no one selected)
        set_membership_members(self.instance, [
            {'uri': URI1, 'alias': ALIAS1},
            {'uri': URI2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn("Not found any joined instance or instance to create a replicaset", res.msg)

    def test_no_joined_instances(self):
        hostvars = {
            ALIAS1: {
                'instance_info': {
                    'console_sock': SOCK1,
                },
            },
            ALIAS2: {
                'replicaset_alias': 'some-rpl',
                'instance_info': {
                    'console_sock': SOCK2,
                },
            },
            'expelled-instance': {
                'replicaset_alias': 'some-rpl',
                'instance_info': {
                    'console_sock': 'some-sock',
                },
                'expelled': True,
            },
            'my-stateboard': {
                'stateboard': True,
            },
        }

        # all instances are in play_hosts
        set_membership_members(self.instance, [
            {'uri': URI1, 'alias': ALIAS1},
            {'uri': URI2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.facts, {'control_instance': {
            'name': ALIAS2,
            'console_sock': SOCK2,
        }})

        # only instances w/o replicaset_alias, expelled and stateboard
        # are in play_hosts
        set_membership_members(self.instance, [
            {'uri': URI1, 'alias': ALIAS1},
            {'uri': URI2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(self.console_sock, hostvars, play_hosts=[
            ALIAS1, 'expelled-instance', 'my-stateboard',
        ])
        self.assertTrue(res.failed, res.facts)
        self.assertIn("Not found any joined instance or instance to create a replicaset", res.msg)

    def tearDown(self):
        self.instance.stop()
        del self.instance
