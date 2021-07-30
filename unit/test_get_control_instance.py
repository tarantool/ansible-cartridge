import sys
import unittest

import module_utils.helpers as helpers
import unit.utils as utils
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


def call_get_control_instance(
    app_name,
    console_sock,
    module_hostvars=None,
    play_hosts=None,
    cluster_disabled_instances='default',
):
    if module_hostvars is None:
        module_hostvars = {}

    if play_hosts is None:
        play_hosts = module_hostvars.keys()

    return get_control_instance({
        'module_hostvars': module_hostvars,
        'cluster_disabled_instances': [] if cluster_disabled_instances == 'default' else cluster_disabled_instances,
        'play_hosts': play_hosts,
        'console_sock': console_sock,
        'app_name': app_name,
    })


def get_instance_hostvars(alias, replicaset_alias=None, run_dir=None, expelled=False, http_port=None):
    return {
        alias: {
            'config': {
                'advertise_uri': '%s-uri' % alias,
                'http_port': http_port,
            },
            'replicaset_alias': replicaset_alias,
            'cartridge_run_dir': run_dir,
            'expelled': expelled,
        }
    }


class TestGetControlInstance(unittest.TestCase):
    def setUp(self):
        self.instance = Instance()
        self.console_sock = self.instance.console_sock
        self.cookie = self.instance.cluster_cookie

        self.instance.start()

    def test_bad_members(self):
        hostvars = get_instance_hostvars('instance-1')
        hostvars.update(get_instance_hostvars('empty-member'))
        hostvars.update(get_instance_hostvars('empty-payload'))

        # empty membership
        self.instance.set_membership_members([])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn("No members in membership", res.msg)

        # empty member
        helpers.WARNINGS = []
        self.instance.set_membership_members([
            utils.get_member('empty-member', empty=True),
            utils.get_member('instance-1'),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed)
        self.assertIn("Incorrect members with the following URIs ignored: empty-member-uri", helpers.WARNINGS)

        # with empty payload
        helpers.WARNINGS = []
        self.instance.set_membership_members([
            utils.get_member('empty-payload', empty_payload=True),
            utils.get_member('instance-1'),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed)
        self.assertIn("Incorrect members with the following URIs ignored: empty-payload-uri", helpers.WARNINGS)

        # without alias
        helpers.WARNINGS = []
        self.instance.set_membership_members([
            utils.get_member('instance-1', with_alias=False),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn("There is no alive instances in the cluster", res.msg)

    def test_one_instance_without_run_dir(self):
        hostvars = get_instance_hostvars('instance-1', 'some-rpl')

        # with UUID and alias
        self.instance.set_membership_members([
            utils.get_member('instance-1', with_uuid=True),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-1',
            'console_sock': '/var/run/tarantool/myapp.instance-1.control',
            'http_port': None,
        })

    def test_one_instance(self):
        hostvars = get_instance_hostvars('instance-1', run_dir='run-dir')

        # with UUID and alias
        self.instance.set_membership_members([
            utils.get_member('instance-1', with_uuid=True),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-1',
            'console_sock': 'run-dir/myapp.instance-1.control',
            'http_port': None,
        })

        # without UUID, instance is dead
        self.instance.set_membership_members([
            utils.get_member('instance-1', with_uuid=False, status='dead'),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn("There is no alive instances in the cluster", res.msg)

        # without UUID
        self.instance.set_membership_members([
            utils.get_member('instance-1', with_uuid=False),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-1',
            'console_sock': 'run-dir/myapp.instance-1.control',
            'http_port': None,
        })

    def test_two_instances(self):
        hostvars = {}
        hostvars.update(get_instance_hostvars('instance-1', run_dir='run-dir-1', http_port=8081))
        hostvars.update(get_instance_hostvars('instance-2', run_dir='run-dir-2', http_port=8082))

        # both with UUID and alias
        # instance-1 is selected since it's URI is
        # first lexicographically
        self.instance.set_membership_members([
            utils.get_member('instance-1', with_uuid=True),
            utils.get_member('instance-2', with_uuid=True),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-1',
            'console_sock': 'run-dir-1/myapp.instance-1.control',
            'http_port': 8081,
        })

        # one with UUID (it is selected)
        self.instance.set_membership_members([
            utils.get_member('instance-1', with_uuid=False),
            utils.get_member('instance-2', with_uuid=True),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-2',
            'console_sock': 'run-dir-2/myapp.instance-2.control',
            'http_port': 8082,
        })

        # one with UUID, but dead
        self.instance.set_membership_members([
            utils.get_member('instance-1', with_uuid=False),
            utils.get_member('instance-2', with_uuid=True, status='dead'),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn("There is no alive joined instances in the cluster", res.msg)

        # one with UUID (but without alias)
        helpers.WARNINGS = []
        self.instance.set_membership_members([
            utils.get_member('instance-1', with_uuid=False),
            utils.get_member('instance-2', with_uuid=True, with_alias=False),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed)
        self.assertIn("Incorrect members with the following URIs ignored: instance-2-uri", helpers.WARNINGS)

        # both without UUID (one is selected)
        self.instance.set_membership_members([
            utils.get_member('instance-1', with_uuid=False),
            utils.get_member('instance-2', with_uuid=False),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-1',
            'console_sock': 'run-dir-1/myapp.instance-1.control',
            'http_port': 8081,
        })

        # both without UUID and dead
        self.instance.set_membership_members([
            utils.get_member('instance-1', with_uuid=False, status='dead'),
            utils.get_member('instance-2', with_uuid=False, status='dead'),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertIn("There is no alive instances in the cluster", res.msg)

    def test_no_joined_instances(self):
        hostvars = {}
        hostvars.update(get_instance_hostvars('instance-4', 'some-rpl', run_dir='run-dir-4', http_port=8084))
        hostvars.update(get_instance_hostvars('instance-3', 'some-rpl', run_dir='run-dir-3', http_port=8083))
        hostvars.update(get_instance_hostvars('instance-2-no-rpl', run_dir='run-dir-2', http_port=8082))
        hostvars.update(get_instance_hostvars(
            'instance-1-expelled', run_dir='run-dir-1', http_port=8081, expelled=True
        ))
        hostvars.update({'my-stateboard': {'stateboard': True}})

        self.instance.set_membership_members([
            utils.get_member('instance-4', with_uuid=False),
            utils.get_member('instance-3', with_uuid=False),
            utils.get_member('instance-2-no-rpl', with_uuid=False),
            utils.get_member('instance-1-expelled', with_uuid=False),
        ])

        # all instances are in play_hosts
        # instance-3 is selected by lexicographic order
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-3',
            'console_sock': 'run-dir-3/myapp.instance-3.control',
            'http_port': 8083,
        })

        # only instances w/o replicaset_alias, expelled and stateboard
        # are in play_hosts
        res = call_get_control_instance('myapp', self.console_sock, hostvars, play_hosts=[
            'instance-2-no-rpl', 'expelled-instance', 'my-stateboard',
        ])
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-2-no-rpl',
            'console_sock': 'run-dir-2/myapp.instance-2-no-rpl.control',
            'http_port': 8082,
        })

        # only expelled and stateboard instances are in play_hosts
        res = call_get_control_instance('myapp', self.console_sock, hostvars, play_hosts=[
            'expelled-instance', 'my-stateboard',
        ])
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-2-no-rpl',
            'console_sock': 'run-dir-2/myapp.instance-2-no-rpl.control',
            'http_port': 8082,
        })

        # instance w/o replicaset alias is deas
        self.instance.set_membership_members([
            utils.get_member('instance-4', with_uuid=False),
            utils.get_member('instance-3', with_uuid=False),
            utils.get_member('instance-2-no-rpl', with_uuid=False, status='dead'),
            utils.get_member('instance-1-expelled', with_uuid=False),
        ])

        # only expelled and stateboard instances are in play_hosts
        res = call_get_control_instance('myapp', self.console_sock, hostvars, play_hosts=[
            'expelled-instance', 'my-stateboard',
        ])
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-3',
            'console_sock': 'run-dir-3/myapp.instance-3.control',
            'http_port': 8083,
        })

    def test_instance_not_in_hostvars(self):
        hostvars = {}
        hostvars.update(get_instance_hostvars('instance-1', 'some-rpl'))
        hostvars.update(get_instance_hostvars('instance-2', 'some-rpl'))

        self.instance.set_membership_members([
            utils.get_member('instance-1', with_uuid=False),
            utils.get_member('instance-2', with_uuid=False),
            utils.get_member('instance-3', with_uuid=True),  # has UUID but not in hostvars
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertTrue(res.failed, res.fact)
        self.assertIn("Membership contains instance 'instance-3' that isn't described in inventor", res.msg)

    def test_twophase_commit_versions(self):
        hostvars = {}
        hostvars.update(get_instance_hostvars('instance-1', 'some-rpl', run_dir='run-dir-1', http_port=8081))
        hostvars.update(get_instance_hostvars('instance-2', 'some-rpl', run_dir='run-dir-2', http_port=8082))
        hostvars.update(get_instance_hostvars('instance-3', 'some-rpl', run_dir='run-dir-3', http_port=8083))

        # instance-3 has lower version of twophase commit
        global twophase_commit_versions
        twophase_commit_versions = {
            'instance-1-uri': 3,
            'instance-2-uri': 2,
            'instance-3-uri': 1,
        }

        # all with UUID and alias - instance-3 is selected
        # (instead of instance-1 by lexicographic order)
        self.instance.set_membership_members([
            utils.get_member('instance-1', with_uuid=True),
            utils.get_member('instance-2', with_uuid=True),
            utils.get_member('instance-3', with_uuid=True),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-3',
            'console_sock': 'run-dir-3/myapp.instance-3.control',
            'http_port': 8083,
        })

        # all without UUID - instance-3 is selected
        # (instead of instance-1 by lexicographic order)
        self.instance.set_membership_members([
            utils.get_member('instance-1', with_uuid=False),
            utils.get_member('instance-2', with_uuid=False),
            utils.get_member('instance-3', with_uuid=False),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-3',
            'console_sock': 'run-dir-3/myapp.instance-3.control',
            'http_port': 8083,
        })

        # instance-1 and instance-2 has UUIDs
        # instance-2 is chosen instead of instance-3 with minimal twophase commit version
        # because instance-2 has minimal twophase commit version between instances with UUIDS
        self.instance.set_membership_members([
            utils.get_member('instance-1', with_uuid=True),
            utils.get_member('instance-2', with_uuid=True),
            utils.get_member('instance-3', with_uuid=False),
        ])
        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'instance-2',
            'console_sock': 'run-dir-2/myapp.instance-2.control',
            'http_port': 8082,
        })

    def test_dead_instances(self):
        # first joined instance is dead
        hostvars = {}
        hostvars.update(get_instance_hostvars('joined-1', 'some-rpl', http_port=8081))
        hostvars.update(get_instance_hostvars('joined-2', 'some-rpl', http_port=8082))
        hostvars.update(get_instance_hostvars('not-joined-1', 'some-rpl', http_port=8083))
        hostvars.update(get_instance_hostvars('not-joined-2', 'some-rpl', http_port=8084))

        self.instance.set_membership_members([
            utils.get_member('joined-1', with_uuid=True, status='dead'),
            utils.get_member('joined-2', with_uuid=True),
            utils.get_member('not-joined-1'),
            utils.get_member('not-joined-2'),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'joined-2',
            'console_sock': '/var/run/tarantool/myapp.joined-2.control',
            'http_port': 8082,
        })

        # all joined instances are dead
        hostvars = {}
        hostvars.update(get_instance_hostvars('joined-1', 'some-rpl'))
        hostvars.update(get_instance_hostvars('joined-2', 'some-rpl'))
        hostvars.update(get_instance_hostvars('not-joined-1', 'some-rpl'))
        hostvars.update(get_instance_hostvars('not-joined-2', 'some-rpl'))

        self.instance.set_membership_members([
            utils.get_member('joined-1', with_uuid=True, status='dead'),
            utils.get_member('joined-2', with_uuid=True, status='suspect'),
            utils.get_member('not-joined-1'),
            utils.get_member('not-joined-2'),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "There is no alive joined instances in the cluster")

        # no joined, first unjoined instance is dead
        hostvars = {}
        hostvars.update(get_instance_hostvars('not-joined-1', 'some-rpl', http_port=8081))
        hostvars.update(get_instance_hostvars('not-joined-2', 'some-rpl', http_port=8082))

        self.instance.set_membership_members([
            utils.get_member('not-joined-1', status='dead'),
            utils.get_member('not-joined-2'),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'not-joined-2',
            'console_sock': '/var/run/tarantool/myapp.not-joined-2.control',
            'http_port': 8082,
        })

        # no joined, first unjoined instance is dead,
        # second doesn't have replicaset alias
        hostvars = {}
        hostvars.update(get_instance_hostvars('not-joined-1', 'some-rpl', http_port=8081))
        hostvars.update(get_instance_hostvars('not-joined-2', http_port=8082))
        hostvars.update(get_instance_hostvars('not-joined-3', 'some-rpl', http_port=8083))

        self.instance.set_membership_members([
            utils.get_member('not-joined-1', status='dead'),
            utils.get_member('not-joined-2'),
            utils.get_member('not-joined-3'),
        ])

        res = call_get_control_instance('myapp', self.console_sock, hostvars)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertEqual(res.fact, {
            'name': 'not-joined-3',
            'console_sock': '/var/run/tarantool/myapp.not-joined-3.control',
            'http_port': 8083,
        })

    def tearDown(self):
        self.instance.stop()
        del self.instance
