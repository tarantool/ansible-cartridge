import sys
import unittest

import module_utils.helpers as helpers
from unit.instance import Instance

sys.modules['ansible.module_utils.helpers'] = helpers
import library.cartridge_get_control_instance as get_control_instance_lib
from library.cartridge_get_control_instance import get_control_instance

twophase_commit_versions = {}


def get_twophase_commit_versions_mock(_, advertise_uris):
    versions = [
        twophase_commit_versions.get(uri, 1) for uri in advertise_uris
    ]
    return versions, None


get_control_instance_lib.get_twophase_commit_versions = get_twophase_commit_versions_mock


def call_get_control_instance(app_name, console_sock, module_hostvars=None, play_hosts=None):
    if module_hostvars is None:
        module_hostvars = {}

    if play_hosts is None:
        play_hosts = module_hostvars.keys()

    return get_control_instance({
        'module_hostvars': module_hostvars,
        'play_hosts': play_hosts,
        'console_sock': console_sock,
        'app_name': app_name,
    })


def get_instance_hostvars(alias, replicaset_alias=None, run_dir=None, expelled=False):
    return {
        alias: {
            'config': {'advertise_uri': '%s-uri' % alias},
            'replicaset_alias': replicaset_alias,
            'cartridge_run_dir': run_dir,
            'expelled': expelled,
        }
    }


def get_member(alias, with_alias=True, with_uuid=False, status=None):
    member = {'uri': '%s-uri' % alias}

    if with_alias:
        member.update({'alias': alias})

    if with_uuid:
        member.update({'uuid': '%s-uuid' % alias})

    if status is not None:
        member.update({'status': status})

    return member


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

    def test_instance_without_alias(self):
        hostvars = get_instance_hostvars('instance-1')

        # with UUID (already bootstrapped) and without alias
        set_membership_members(self.instance, [
            get_member('instance-1', with_uuid=True, with_alias=False),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn("Instance with URI instance-1-uri payload doesn't contain alias", res.msg)

    def test_one_instance_without_run_dir(self):
        hostvars = get_instance_hostvars('instance-1', 'some-rpl')

        # with UUID and alias
        set_membership_members(self.instance, [
            get_member('instance-1', with_uuid=True),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-1',
            'console_sock': '/var/run/tarantool/myapp.instance-1.control',
        })

    def test_one_instance(self):
        hostvars = get_instance_hostvars('instance-1', run_dir='run-dir')

        # with UUID and alias
        set_membership_members(self.instance, [
            get_member('instance-1', with_uuid=True),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-1',
            'console_sock': 'run-dir/myapp.instance-1.control',
        })

        # without UUID
        set_membership_members(self.instance, [
            get_member('instance-1', with_uuid=False),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn("There is no alive instances", res.msg)

    def test_two_instances(self):
        hostvars = {}
        hostvars.update(get_instance_hostvars('instance-1', run_dir='run-dir-1'))
        hostvars.update(get_instance_hostvars('instance-2', run_dir='run-dir-2'))

        # both with UUID and alias
        # instance-1 is selected since it's URI is
        # first lexicographically
        set_membership_members(self.instance, [
            get_member('instance-1', with_uuid=True),
            get_member('instance-2', with_uuid=True),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-1',
            'console_sock': 'run-dir-1/myapp.instance-1.control',
        })

        # one with UUID (it is selected)
        set_membership_members(self.instance, [
            get_member('instance-1', with_uuid=False),
            get_member('instance-2', with_uuid=True),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-2',
            'console_sock': 'run-dir-2/myapp.instance-2.control',
        })

        # one with UUID (but without alias)
        set_membership_members(self.instance, [
            get_member('instance-1', with_uuid=False),
            get_member('instance-2', with_uuid=True, with_alias=False),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn("Instance with URI instance-2-uri payload doesn't contain alias", res.msg)

        # both without UUID (no one selected)
        set_membership_members(self.instance, [
            get_member('instance-1', with_uuid=False),
            get_member('instance-2', with_uuid=False),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn("There is no alive instances", res.msg)

    def test_no_joined_instances(self):
        hostvars = {}
        hostvars.update(get_instance_hostvars('instance-4', 'some-rpl', run_dir='run-dir-4'))
        hostvars.update(get_instance_hostvars('instance-3', 'some-rpl', run_dir='run-dir-3'))
        hostvars.update(get_instance_hostvars('instance-2-no-rpl', run_dir='run-dir-2'))
        hostvars.update(get_instance_hostvars('instance-1-expelled', run_dir='run-dir-1'))
        hostvars.update({'my-stateboard': {'stateboard': True}})

        set_membership_members(self.instance, [
            get_member('instance-4', with_uuid=False),
            get_member('instance-3', with_uuid=False),
            get_member('instance-2-no-rpl', with_uuid=False),
            get_member('instance-1-expelled', with_uuid=False),
        ])

        # all instances are in play_hosts
        # instance-3 is selected by lexicographic order
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-3',
            'console_sock': 'run-dir-3/myapp.instance-3.control',
        })

        # only instances w/o replicaset_alias, expelled and stateboard
        # are in play_hosts
        res = call_get_control_instance('myapp', self.console_sock, hostvars, play_hosts=[
            'instance-not-in-replicaset', 'expelled-instance', 'my-stateboard',
        ])
        self.assertTrue(res.failed, res.fact)
        self.assertIn("There is no alive instances", res.msg)

    def test_instance_not_in_hostvars(self):
        hostvars = {}
        hostvars.update(get_instance_hostvars('instance-1', 'some-rpl'))
        hostvars.update(get_instance_hostvars('instance-2', 'some-rpl'))

        set_membership_members(self.instance, [
            get_member('instance-1', with_uuid=False),
            get_member('instance-2', with_uuid=False),
            get_member('instance-3', with_uuid=True),  # has UUID but not in hostvars
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertTrue(res.failed, res.fact)
        self.assertIn("Membership contains instance instance-3 that isn't described in inventor", res.msg)

    def test_twophase_commit_versions(self):
        hostvars = {}
        hostvars.update(get_instance_hostvars('instance-1', 'some-rpl', run_dir='run-dir-1'))
        hostvars.update(get_instance_hostvars('instance-2', 'some-rpl', run_dir='run-dir-2'))
        hostvars.update(get_instance_hostvars('instance-3', 'some-rpl', run_dir='run-dir-3'))

        # instance-3 has lower version of twophase commit
        global twophase_commit_versions
        twophase_commit_versions = {
            'instance-1-uri': 3,
            'instance-2-uri': 2,
            'instance-3-uri': 1,
        }

        # all with UUID and alias - instance-3 is selected
        # (instead of instance-1 by lexicographic order)
        set_membership_members(self.instance, [
            get_member('instance-1', with_uuid=True),
            get_member('instance-2', with_uuid=True),
            get_member('instance-3', with_uuid=True),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-3',
            'console_sock': 'run-dir-3/myapp.instance-3.control',
        })

        # all without UUID - instance-3 is selected
        # (instead of instance-1 by lexicographic order)
        set_membership_members(self.instance, [
            get_member('instance-1', with_uuid=False),
            get_member('instance-2', with_uuid=False),
            get_member('instance-3', with_uuid=False),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-3',
            'console_sock': 'run-dir-3/myapp.instance-3.control',
        })

        # instance-1 and instance-2 has UUIDs
        # instance-2 is chosen instead of instance-3 with minimal twophase commit version
        # because instance-2 has minimal twophase commit version between instances with UUIDS
        set_membership_members(self.instance, [
            get_member('instance-1', with_uuid=True),
            get_member('instance-2', with_uuid=True),
            get_member('instance-3', with_uuid=False),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-2',
            'console_sock': 'run-dir-2/myapp.instance-2.control',
        })

    def test_dead_instances(self):
        # first joined instance is dead
        hostvars = {}
        hostvars.update(get_instance_hostvars('joined-1', 'some-rpl'))
        hostvars.update(get_instance_hostvars('joined-2', 'some-rpl'))
        hostvars.update(get_instance_hostvars('not-joined-1', 'some-rpl'))
        hostvars.update(get_instance_hostvars('not-joined-2', 'some-rpl'))

        set_membership_members(self.instance, [
            get_member('joined-1', with_uuid=True, status='dead'),
            get_member('joined-2', with_uuid=True),
            get_member('not-joined-1'),
            get_member('not-joined-2'),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'joined-2',
            'console_sock': '/var/run/tarantool/myapp.joined-2.control',
        })

        # all joined instances are dead
        hostvars = {}
        hostvars.update(get_instance_hostvars('joined-1', 'some-rpl'))
        hostvars.update(get_instance_hostvars('joined-2', 'some-rpl'))
        hostvars.update(get_instance_hostvars('not-joined-1', 'some-rpl'))
        hostvars.update(get_instance_hostvars('not-joined-2', 'some-rpl'))

        set_membership_members(self.instance, [
            get_member('joined-1', with_uuid=True, status='dead'),
            get_member('joined-2', with_uuid=True, status='suspect'),
            get_member('not-joined-1'),
            get_member('not-joined-2'),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "There is no alive instances in the cluster")

        # no joined, first unjoined instance is dead
        hostvars = {}
        hostvars.update(get_instance_hostvars('not-joined-1', 'some-rpl'))
        hostvars.update(get_instance_hostvars('not-joined-2', 'some-rpl'))

        set_membership_members(self.instance, [
            get_member('not-joined-1', status='dead'),
            get_member('not-joined-2'),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'not-joined-2',
            'console_sock': '/var/run/tarantool/myapp.not-joined-2.control',
        })

        # no joined, first unjoined instance is dead,
        # second doesn't have replicaset alias
        hostvars = {}
        hostvars.update(get_instance_hostvars('not-joined-1', 'some-rpl'))
        hostvars.update(get_instance_hostvars('not-joined-2'))
        hostvars.update(get_instance_hostvars('not-joined-3', 'some-rpl'))

        set_membership_members(self.instance, [
            get_member('not-joined-1', status='dead'),
            get_member('not-joined-2'),
            get_member('not-joined-3'),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'not-joined-3',
            'console_sock': '/var/run/tarantool/myapp.not-joined-3.control',
        })

    def tearDown(self):
        self.instance.stop()
        del self.instance
