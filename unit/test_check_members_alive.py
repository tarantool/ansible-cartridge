import sys
import unittest

import module_utils.helpers as helpers
import unit.utils as utils
from unit.instance import Instance

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_check_members_alive import check_members_alive


def call_check_members_alive(console_sock, allowed_states=['RolesConfigured']):
    return check_members_alive({
        'console_sock': console_sock,
        'allowed_states': allowed_states,
    })


class TestInstanceStarted(unittest.TestCase):
    def setUp(self):
        self.instance = Instance()
        self.console_sock = self.instance.console_sock
        self.cookie = self.instance.cluster_cookie

        self.instance.start()

    def test_no_joined_instances(self):
        self.instance.set_membership_members([
            utils.get_member('instance-1'),
            utils.get_member('instance-2'),
            # UUID from membership doesn't matter, instances from topology conf are checked
            utils.get_member('instance-3', with_uuid=True),
        ])

        res = call_check_members_alive(self.console_sock)
        self.assertTrue(res.failed)
        self.assertIn("Instances aren't joined to cluster yet", res.msg)

    def test_joined_instances_alive(self):
        self.instance.add_replicaset(
            alias='r1',
            instances=['instance-1-joined', 'instance-2-joined', 'instance-3-joined'],
        )

        self.instance.set_membership_members([
            utils.get_member('instance-1-joined', with_uuid=True, status='alive', state='RolesConfigured'),
            utils.get_member('instance-2-joined', with_uuid=True, status='alive', state='RolesConfigured'),
            utils.get_member('instance-3-joined', with_uuid=True, status='alive', state='RolesConfigured'),
            utils.get_member('instance-4', status='dead', state='Unconfigured'),
            utils.get_member('instance-5', status='dead', state='Unconfigured'),
        ])

        res = call_check_members_alive(self.console_sock)
        self.assertFalse(res.failed, res.msg)

    def test_bad_joined_instances(self):
        self.instance.add_replicaset(
            alias='r1',
            instances=['instance-1-joined', 'instance-2-joined', 'instance-3-joined', 'instance-4-joined'],
        )

        self.instance.set_membership_members([
            utils.get_member('instance-1-joined', with_uuid=True, status='alive', state='RolesConfigured'),
            utils.get_member('instance-2-joined', uuid='bad-uuid', status='alive', state='RolesConfigured'),
            utils.get_member('instance-3-joined', with_uuid=True, status='dead', state='RolesConfigured'),
            utils.get_member('instance-4-joined', with_uuid=True, status='alive', state='OperationError'),
            utils.get_member('instance-5', status='dead', state='Unconfigured'),
            utils.get_member('instance-6', status='dead', state='Unconfigured'),
        ])

        res = call_check_members_alive(self.console_sock)
        self.assertTrue(res.failed)
        self.assertEqual(
            res.msg,
            "Some instances aren't alive: "
            "instance-2-joined-uri uuid mismatch: expected instance-2-joined-uuid, have bad-uuid, "
            "instance-3-joined-uri status is dead, "
            "instance-4-joined-uri state is OperationError"
        )

    def test_allowed_states(self):
        self.instance.add_replicaset(
            alias='r1',
            instances=['instance-1-joined', 'instance-2-joined', 'instance-3-joined'],
        )

        self.instance.set_membership_members([
            utils.get_member('instance-1-joined', with_uuid=True, status='alive', state='SomeState'),
            utils.get_member('instance-2-joined', with_uuid=True, status='alive', state='SomeOtherState'),
            utils.get_member('instance-3-joined', with_uuid=True, status='alive', state='OneMoreState'),
            utils.get_member('instance-4', status='dead', state='Unconfigured'),
            utils.get_member('instance-5', status='dead', state='Unconfigured'),
        ])

        res = call_check_members_alive(self.console_sock, allowed_states=[
            'SomeState', 'SomeOtherState', 'OneMoreState',
        ])
        self.assertFalse(res.failed, res.msg)

    def tearDown(self):
        self.instance.stop()
        del self.instance
