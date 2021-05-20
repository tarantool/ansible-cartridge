import sys
import unittest
from parameterized import parameterized

import module_utils.helpers as helpers
from unit.instance import Instance

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_check_cluster_issues import check_cluster_issues


ISSUES_WARN_HEADER = '* Issues (warning): *********************************************'
ISSUES_CRIT_HEADER = '* Issues (critical): *********************************************'
ISSUES_OTHER_HEADER = '* Issues (other-level): *********************************************'


def call_check_cluster_issues(console_sock, show_issues=True, allow_warnings=False):
    return check_cluster_issues({
        'console_sock': console_sock,
        'show_issues': show_issues,
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

    @parameterized.expand([
        [True],
        [False],
    ])
    def test_issues(self, show_issues):
        set_issues(self.instance, [
            {'level': 'critical', 'message': 'Some critical issue 1'},
            {'level': 'warning', 'message': 'Some warning issue 2'},
            {'level': 'critical', 'message': 'Some critical issue 3'},
            {'level': 'other-level', 'message': 'Some other-level issue 4'},
            {'level': 'warning', 'message': 'Some warning issue 5'},
            {'level': 'critical', 'message': 'Some critical issue 6'},
        ])

        res = call_check_cluster_issues(self.console_sock, show_issues=show_issues)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 6 issues")

        if not show_issues:
            self.assertEqual(len(get_warnings(res)), 0)
        else:
            self.assertEqual(get_warnings(res), [
                ISSUES_CRIT_HEADER,
                'Some critical issue 1',
                'Some critical issue 3',
                'Some critical issue 6',
                ISSUES_OTHER_HEADER,
                'Some other-level issue 4',
                ISSUES_WARN_HEADER,
                'Some warning issue 2',
                'Some warning issue 5',
            ])

        # only critical
        set_issues(self.instance, [
            {'level': 'critical', 'message': 'Some critical issue 1'},
            {'level': 'critical', 'message': 'Some critical issue 3'},
            {'level': 'critical', 'message': 'Some critical issue 6'},
        ])

        res = call_check_cluster_issues(self.console_sock, show_issues=show_issues)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 3 issues")

        if not show_issues:
            self.assertEqual(len(get_warnings(res)), 0)
        else:
            self.assertEqual(get_warnings(res), [
                ISSUES_CRIT_HEADER,
                'Some critical issue 1',
                'Some critical issue 3',
                'Some critical issue 6',
            ])

        # only warnings
        set_issues(self.instance, [
            {'level': 'warning', 'message': 'Some warning issue 2'},
            {'level': 'warning', 'message': 'Some warning issue 5'},
        ])

        res = call_check_cluster_issues(self.console_sock, show_issues=show_issues)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 2 issues")

        if not show_issues:
            self.assertEqual(len(get_warnings(res)), 0)
        else:
            self.assertEqual(get_warnings(res), [
                ISSUES_WARN_HEADER,
                'Some warning issue 2',
                'Some warning issue 5',
            ])

        # only unknown
        set_issues(self.instance, [
            {'level': 'other-level', 'message': 'Some other-level issue 4'},
        ])

        res = call_check_cluster_issues(self.console_sock, show_issues=show_issues)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 1 issues")

        if not show_issues:
            self.assertEqual(len(get_warnings(res)), 0)
        else:
            self.assertEqual(get_warnings(res), [
                ISSUES_OTHER_HEADER,
                'Some other-level issue 4',
            ])

    @parameterized.expand([
        [True],
        [False],
    ])
    def test_warnings(self, show_issues):
        set_issues(self.instance, [
            {'level': 'critical', 'message': 'Some critical issue 1'},
            {'level': 'warning', 'message': 'Some warning issue 2'},
            {'level': 'critical', 'message': 'Some critical issue 3'},
            {'level': 'other-level', 'message': 'Some other-level issue 4'},
            {'level': 'warning', 'message': 'Some warning issue 5'},
            {'level': 'critical', 'message': 'Some critical issue 6'},
        ])

        res = call_check_cluster_issues(self.console_sock, allow_warnings=True, show_issues=show_issues)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 4 critical issues")

        if not show_issues:
            self.assertEqual(len(get_warnings(res)), 0)
        else:
            self.assertEqual(get_warnings(res), [
                ISSUES_CRIT_HEADER,
                'Some critical issue 1',
                'Some critical issue 3',
                'Some critical issue 6',
                ISSUES_OTHER_HEADER,
                'Some other-level issue 4',
                ISSUES_WARN_HEADER,
                'Some warning issue 2',
                'Some warning issue 5',
            ])

        # only warnings
        set_issues(self.instance, [
            {'level': 'warning', 'message': 'Some warning issue 2'},
            {'level': 'warning', 'message': 'Some warning issue 5'},
        ])

        res = call_check_cluster_issues(self.console_sock, allow_warnings=True, show_issues=show_issues)
        self.assertFalse(res.failed)

        if not show_issues:
            self.assertEqual(len(get_warnings(res)), 0)
        else:
            self.assertEqual(get_warnings(res), [
                ISSUES_WARN_HEADER,
                'Some warning issue 2',
                'Some warning issue 5',
            ])

        # only critical
        set_issues(self.instance, [
            {'level': 'critical', 'message': 'Some critical issue 1'},
            {'level': 'critical', 'message': 'Some critical issue 3'},
            {'level': 'critical', 'message': 'Some critical issue 6'},
        ])

        res = call_check_cluster_issues(self.console_sock, allow_warnings=True, show_issues=show_issues)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 3 critical issues")

        if not show_issues:
            self.assertEqual(len(get_warnings(res)), 0)
        else:
            self.assertEqual(get_warnings(res), [
                ISSUES_CRIT_HEADER,
                'Some critical issue 1',
                'Some critical issue 3',
                'Some critical issue 6',
            ])

        # only unknown
        set_issues(self.instance, [
            {'level': 'other-level', 'message': 'Some other-level issue 4'},
        ])

        res = call_check_cluster_issues(self.console_sock, allow_warnings=True, show_issues=show_issues)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 1 critical issues")

        if not show_issues:
            self.assertEqual(len(get_warnings(res)), 0)
        else:
            self.assertEqual(get_warnings(res), [
                ISSUES_OTHER_HEADER,
                'Some other-level issue 4',
            ])

    @parameterized.expand([
        [True],
        [False],
    ])
    def test_list_on_cluster_returns_error(self, show_issues):
        set_issues(self.instance, [
            {'level': 'critical', 'message': 'Some critical issue 1'},
            {'level': 'warning', 'message': 'Some warning issue 2'},
            {'level': 'critical', 'message': 'Some critical issue 3'},
            {'level': 'other-level', 'message': 'Some other-level issue 4'},
            {'level': 'warning', 'message': 'Some warning issue 5'},
            {'level': 'critical', 'message': 'Some critical issue 6'},
        ])

        self.instance.set_fail_on('issues_list_on_clister')

        res = call_check_cluster_issues(self.console_sock, show_issues=show_issues)
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, "Cluster has 6 issues")

        warnings = get_warnings(res)
        self.assertEqual(warnings[0], 'Received error on getting list of cluster issues: cartridge err')

        if not show_issues:
            self.assertEqual(len(warnings), 1)
        else:
            self.assertEqual(warnings[1:], [
                ISSUES_CRIT_HEADER,
                'Some critical issue 1',
                'Some critical issue 3',
                'Some critical issue 6',
                ISSUES_OTHER_HEADER,
                'Some other-level issue 4',
                ISSUES_WARN_HEADER,
                'Some warning issue 2',
                'Some warning issue 5',
            ])

    def tearDown(self):
        self.instance.stop()
        del self.instance
