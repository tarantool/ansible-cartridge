import os
import unittest

import library.cartridge_get_control_instance as get_control_instance_lib
from library.cartridge_get_control_instance import get_control_instance
from unit.instance import Instance

twophase_commit_versions = {}


def get_twophase_commit_versions_mock(_, advertise_uris):
    versions = [
        twophase_commit_versions.get(uri, 1) for uri in advertise_uris
    ]
    return versions, None


get_control_instance_lib.get_twophase_commit_versions = get_twophase_commit_versions_mock


def call_get_control_instance(app_name, console_sock, role_vars=None, play_hosts=None):
    if role_vars is None:
        role_vars = {}

    if play_hosts is None:
        play_hosts = role_vars.keys()

    hostvars = {}
    for instance_name, instance_role_vars in role_vars.items():
        hostvars[instance_name] = {
            'role_vars': instance_role_vars
        }

    return get_control_instance({
        'hostvars': hostvars,
        'play_hosts': play_hosts,
        'console_sock': console_sock,
        'app_name': app_name,
    })


URI1 = '127.0.0.1:3301'
URI2 = '127.0.0.1:3302'
URI3 = '127.0.0.1:3303'

UUID1 = 'uuid-1'
UUID2 = 'uuid-2'
UUID3 = 'uuid-3'

APP_NAME = 'myapp'

ALIAS1 = 'alias-1'
ALIAS2 = 'alias-2'
ALIAS3 = 'alias-3'

RUN_DIR1 = '%s-run-dir' % ALIAS1
RUN_DIR2 = '%s-run-dir' % ALIAS2
RUN_DIR3 = '%s-run-dir' % ALIAS3

SOCK1 = os.path.join(RUN_DIR1, '%s.%s.control' % (APP_NAME, ALIAS1))
SOCK2 = os.path.join(RUN_DIR2, '%s.%s.control' % (APP_NAME, ALIAS2))
SOCK3 = os.path.join(RUN_DIR3, '%s.%s.control' % (APP_NAME, ALIAS3))


def set_membership_members(instance, specified_members, with_payload=True):
    members = {}

    for m in specified_members:
        uri = m['uri']
        member = {
            'uri': uri,
            'status': m.get('status', 'alive'),
            'incarnation': 1,
        }

        if with_payload:
            member.update({
                'payload': {
                    'uuid': m.get('uuid'),
                    'alias': m.get('alias')
                }
            })

        members[uri] = member

    instance.set_variable('membership_members', members)


class TestGetControlInstance(unittest.TestCase):
    def setUp(self):
        self.instance = Instance()
        self.console_sock = self.instance.console_sock
        self.cookie = self.instance.cluster_cookie

        self.instance.start()

    def test_instance_without_payload(self):
        # with UUID (already bootstrapped) and without alias
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1},
        ], with_payload=False)
        res = call_get_control_instance(APP_NAME, self.console_sock)
        self.assertTrue(res.failed)
        self.assertIn('Instance %s does not contain payload' % URI1, res.msg)

    def test_instance_without_alias(self):
        # with UUID (already bootstrapped) and without alias
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1},
        ])
        res = call_get_control_instance(APP_NAME, self.console_sock)
        self.assertTrue(res.failed)
        self.assertIn('Instance %s payload does not contain alias' % URI1, res.msg)

    def test_one_instance_without_run_dir(self):
        hostvars = {
            ALIAS1: {'config': {'advertise_uri': URI1}},
        }

        # with UUID and alias
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1, 'alias': ALIAS1},
        ])
        res = call_get_control_instance(APP_NAME, self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': ALIAS1,
            'console_sock': os.path.join('/var/run/tarantool', '%s.%s.control' % (APP_NAME, ALIAS1)),
        })

    def test_one_instance(self):
        hostvars = {
            ALIAS1: {'cartridge_run_dir': RUN_DIR1, 'config': {'advertise_uri': URI1}},
        }

        # with UUID and alias
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1, 'alias': ALIAS1},
        ])
        res = call_get_control_instance(APP_NAME, self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': ALIAS1,
            'console_sock': SOCK1,
        })

        # without UUID
        set_membership_members(self.instance, [
            {'uri': URI1, 'alias': ALIAS1},
        ])
        res = call_get_control_instance(APP_NAME, self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn("Not found any joined instance or instance to create a replicaset", res.msg)

    def test_two_instances(self):
        hostvars = {
            ALIAS1: {'cartridge_run_dir': RUN_DIR1, 'config': {'advertise_uri': URI1}},
            ALIAS2: {'cartridge_run_dir': RUN_DIR2, 'config': {'advertise_uri': URI2}},
        }

        # both with UUID and alias
        # URI1 is selected since it's first lexicographically
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1, 'alias': ALIAS1},
            {'uri': URI2, 'uuid': UUID2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(APP_NAME, self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': ALIAS1,
            'console_sock': SOCK1,
        })

        # one with UUID (it is selected)
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1, 'alias': ALIAS1},
            {'uri': URI2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(APP_NAME, self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': ALIAS1,
            'console_sock': SOCK1,
        })

        # one with UUID (but without alias)
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1},
            {'uri': URI2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(APP_NAME, self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn('Instance %s payload does not contain alias' % URI1, res.msg)

        # both without UUID (no one selected)
        set_membership_members(self.instance, [
            {'uri': URI1, 'alias': ALIAS1},
            {'uri': URI2, 'alias': ALIAS2},
        ])
        res = call_get_control_instance(APP_NAME, self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn("Not found any joined instance or instance to create a replicaset", res.msg)

    def test_no_joined_instances(self):
        hostvars = {
            ALIAS1: {
                'config': {'advertise_uri': URI1},
                'cartridge_run_dir': RUN_DIR1,
                'replicaset_alias': 'some-rpl',
            },
            ALIAS2: {
                'config': {'advertise_uri': URI2},
                'cartridge_run_dir': RUN_DIR2,
                'replicaset_alias': 'some-rpl',
            },
            'instance-not-in-replicaset': {
                'config': {'advertise_uri': 'uri-not-in-replicaset'},
            },
            'expelled-instance': {
                'config': {'advertise_uri': 'uri-expelled'},
                'replicaset_alias': 'some-rpl',
                'cartridge_run_dir': RUN_DIR1,
                'expelled': True,
            },
            'my-stateboard': {
                'stateboard': True,
            },
        }

        set_membership_members(self.instance, [
            {'uri': URI1, 'alias': ALIAS1},
            {'uri': URI2, 'alias': ALIAS2},
        ])

        # all instances are in play_hosts
        # URI1 is selected by lexicographic order
        res = call_get_control_instance(APP_NAME, self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': ALIAS1,
            'console_sock': SOCK1,
        })

        # only instances w/o replicaset_alias, expelled and stateboard
        # are in play_hosts
        res = call_get_control_instance(APP_NAME, self.console_sock, hostvars, play_hosts=[
            'instance-not-in-replicaset', 'expelled-instance', 'my-stateboard',
        ])
        self.assertTrue(res.failed, res.fact)
        self.assertIn("Not found any joined instance or instance to create a replicaset", res.msg)

    def test_instance_not_in_hostvars(self):
        hostvars = {
            ALIAS1: {},
            ALIAS2: {},
        }

        set_membership_members(self.instance, [
            {'uri': URI1, 'alias': ALIAS1},
            {'uri': URI2, 'alias': ALIAS2},
            {'uri': URI3, 'alias': ALIAS3, 'uuid': UUID3},  # has UUID but not in hostvars
        ])

        res = call_get_control_instance(APP_NAME, self.console_sock, hostvars)
        self.assertTrue(res.failed, res.fact)
        self.assertIn("Not found any joined instance or instance to create a replicaset", res.msg)

    def test_instance_is_not_alive(self):
        hostvars = {
            ALIAS1: {},
            ALIAS2: {},
        }

        set_membership_members(self.instance, [
            {'uri': URI1, 'alias': ALIAS1},
            {'uri': URI2, 'alias': ALIAS2, 'uuid': UUID3, 'status': 'dead'},  # has UUID but dead
        ])

        res = call_get_control_instance(APP_NAME, self.console_sock, hostvars)
        self.assertTrue(res.failed, res.fact)
        self.assertIn("Not found any joined instance or instance to create a replicaset", res.msg)

    def test_twophase_commit_versions(self):
        hostvars = {
            ALIAS1: {
                'cartridge_run_dir': RUN_DIR1,
                'config': {'advertise_uri': URI1},
                'replicaset_alias': 'rpl-1',
            },
            ALIAS2: {
                'cartridge_run_dir': RUN_DIR2,
                'config': {'advertise_uri': URI2},
                'replicaset_alias': 'rpl-1',
            },
            ALIAS3: {
                'cartridge_run_dir': RUN_DIR3,
                'config': {'advertise_uri': URI3},
                'replicaset_alias': 'rpl-1',
            },
        }

        # URI3 has lower version of twophase commit
        global twophase_commit_versions
        twophase_commit_versions = {
            URI1: 3,
            URI2: 2,
            URI3: 1,
        }

        # all with UUID and alias - URI3 is selected
        # (instead of URI1 by lexicographic order)
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1, 'alias': ALIAS1},
            {'uri': URI2, 'uuid': UUID2, 'alias': ALIAS2},
            {'uri': URI3, 'uuid': UUID3, 'alias': ALIAS3},
        ])
        res = call_get_control_instance(APP_NAME, self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': ALIAS3,
            'console_sock': SOCK3,
        })

        # both without UUID and alias - URI3 is selected
        # (instead of URI1 by lexicographic order)
        set_membership_members(self.instance, [
            {'uri': URI1, 'alias': ALIAS1},
            {'uri': URI2, 'alias': ALIAS2},
            {'uri': URI3, 'alias': ALIAS3},
        ])
        res = call_get_control_instance(APP_NAME, self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': ALIAS3,
            'console_sock': SOCK3,
        })

        # URI1 and URI2 has UUIDs
        # URI2 is chosen instead of URI3 with minimal twophase commit version
        # because URI2 has minimal twophase commit version between instances with UUIDS
        set_membership_members(self.instance, [
            {'uri': URI1, 'uuid': UUID1, 'alias': ALIAS1},
            {'uri': URI2, 'uuid': UUID2, 'alias': ALIAS2},
            {'uri': URI3, 'alias': ALIAS3},
        ])
        res = call_get_control_instance(APP_NAME, self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': ALIAS2,
            'console_sock': SOCK2,
        })

    def tearDown(self):
        self.instance.stop()
        del self.instance
