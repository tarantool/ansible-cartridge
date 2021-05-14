import sys
import unittest

import module_utils.helpers as helpers
from unit.instance import Instance

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_check_cluster_issues import check_cluster_issues


def call_check_cluster_issues(console_sock, allow_warnings=False):
    return check_cluster_issues({
        'console_sock': console_sock,
        'allow_warnings': allow_warnings,
    })


def set_issues(instance, issues):
    formatted_issues = [
        {
            'level': issue['level'],
            'topic': 'some-topic',
            'replicaset_uuid': 'some-replicaset-uuid',
            'instance_uuid': 'some-instance-uuid',
            'message': issue['message'],
        }
        for issue in issues
    ]

    instance.set_variable('issues', formatted_issues)


def get_warnings(res):
    res_json = res.get_exit_json()
    return res_json.get('warnings')


class TestInstanceStarted(unittest.TestCase):
    def setUp(self):
        self.instance = Instance()
        self.console_sock = self.instance.console_sock
        self.cookie = self.instance.cluster_cookie

        self.instance.start()

    def test_no_issues(self):
        res = call_check_cluster_issues(self.console_sock)
        self.assertFalse(res.failed, res.msg)

    def test_issues(self):
        set_issues(self.instance, [
            {'level': 'critical', 'message': 'Some critical issue 1'},
            {'level': 'warning', 'message': 'Some warning issue 2'},
            {'level': 'critical', 'message': 'Some critical issue 3'},
            {'level': 'other-level', 'message': 'Some other-level issue 4'},
            {'level': 'warning', 'message': 'Some warning issue 5'},
            {'level': 'critical', 'message': 'Some critical issue 6'},
        ])

        res = call_check_cluster_issues(self.console_sock)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 6 issues")
        self.assertEqual(get_warnings(res), [
            'Issues (critical):',
            'Some critical issue 1',
            'Some critical issue 3',
            'Some critical issue 6',
            '',
            'Issues (unknown):',
            'Some other-level issue 4',
            '',
            'Issues (warning):',
            'Some warning issue 2',
            'Some warning issue 5',
        ])

        # only critical
        set_issues(self.instance, [
            {'level': 'critical', 'message': 'Some critical issue 1'},
            {'level': 'critical', 'message': 'Some critical issue 3'},
            {'level': 'critical', 'message': 'Some critical issue 6'},
        ])

        res = call_check_cluster_issues(self.console_sock)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 3 issues")
        self.assertEqual(get_warnings(res), [
            'Issues (critical):',
            'Some critical issue 1',
            'Some critical issue 3',
            'Some critical issue 6',
        ])

        # only warnings
        set_issues(self.instance, [
            {'level': 'warning', 'message': 'Some warning issue 2'},
            {'level': 'warning', 'message': 'Some warning issue 5'},
        ])

        res = call_check_cluster_issues(self.console_sock)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 2 issues")
        self.assertEqual(get_warnings(res), [
            'Issues (warning):',
            'Some warning issue 2',
            'Some warning issue 5',
        ])

        # only unknown
        set_issues(self.instance, [
            {'level': 'other-level', 'message': 'Some other-level issue 4'},
        ])

        res = call_check_cluster_issues(self.console_sock)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 1 issues")
        self.assertEqual(get_warnings(res), [
            'Issues (unknown):',
            'Some other-level issue 4',
        ])

    def test_warnings(self):
        set_issues(self.instance, [
            {'level': 'critical', 'message': 'Some critical issue 1'},
            {'level': 'warning', 'message': 'Some warning issue 2'},
            {'level': 'critical', 'message': 'Some critical issue 3'},
            {'level': 'other-level', 'message': 'Some other-level issue 4'},
            {'level': 'warning', 'message': 'Some warning issue 5'},
            {'level': 'critical', 'message': 'Some critical issue 6'},
        ])

        res = call_check_cluster_issues(self.console_sock, allow_warnings=True)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 4 critical issues")
        self.assertEqual(get_warnings(res), [
            'Issues (critical):',
            'Some critical issue 1',
            'Some critical issue 3',
            'Some critical issue 6',
            '',
            'Issues (unknown):',
            'Some other-level issue 4',
            '',
            'Issues (warning):',
            'Some warning issue 2',
            'Some warning issue 5',
        ])

        # only warnings
        set_issues(self.instance, [
            {'level': 'warning', 'message': 'Some warning issue 2'},
            {'level': 'warning', 'message': 'Some warning issue 5'},
        ])

        res = call_check_cluster_issues(self.console_sock, allow_warnings=True)
        self.assertFalse(res.failed)
        self.assertEqual(get_warnings(res), [
            'Issues (warning):',
            'Some warning issue 2',
            'Some warning issue 5',
        ])

        # only critical
        set_issues(self.instance, [
            {'level': 'critical', 'message': 'Some critical issue 1'},
            {'level': 'critical', 'message': 'Some critical issue 3'},
            {'level': 'critical', 'message': 'Some critical issue 6'},
        ])

        res = call_check_cluster_issues(self.console_sock, allow_warnings=True)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 3 critical issues")
        self.assertEqual(get_warnings(res), [
            'Issues (critical):',
            'Some critical issue 1',
            'Some critical issue 3',
            'Some critical issue 6',
        ])

        # only unknown
        set_issues(self.instance, [
            {'level': 'other-level', 'message': 'Some other-level issue 4'},
        ])

        res = call_check_cluster_issues(self.console_sock, allow_warnings=True)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 1 critical issues")
        self.assertEqual(get_warnings(res), [
            'Issues (unknown):',
            'Some other-level issue 4',
        ])

    def test_list_on_cluster_returns_error(self):
        set_issues(self.instance, [
            {'level': 'critical', 'message': 'Some critical issue 1'},
            {'level': 'warning', 'message': 'Some warning issue 2'},
            {'level': 'critical', 'message': 'Some critical issue 3'},
            {'level': 'other-level', 'message': 'Some other-level issue 4'},
            {'level': 'warning', 'message': 'Some warning issue 5'},
            {'level': 'critical', 'message': 'Some critical issue 6'},
        ])

        self.instance.set_fail_on('issues_list_on_clister')

        res = call_check_cluster_issues(self.console_sock)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 6 issues")
        self.assertEqual(get_warnings(res), [
            'Received error on getting list of cluster issues: cartridge err',
            '',
            'Issues (critical):',
            'Some critical issue 1',
            'Some critical issue 3',
            'Some critical issue 6',
            '',
            'Issues (unknown):',
            'Some other-level issue 4',
            '',
            'Issues (warning):',
            'Some warning issue 2',
            'Some warning issue 5',
        ])

    def tearDown(self):
        self.instance.stop()
        del self.instance
