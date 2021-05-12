#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'allow_warnings': {'required': True, 'type': 'bool'},
    'console_sock': {'required': True, 'type': 'str'},
}


def get_messages(**issues_by_level):
    messages = []
    for level, issues in issues_by_level.items():
        if not issues:
            continue

        if messages:
            messages += ['']

        messages += ['Issues (%s):' % level]
        messages += [issue['message'] for issue in issues]

    return messages


def check_cluster_issues(params):
    allow_warnings = params['allow_warnings']
    console_sock = params['console_sock']

    control_console = helpers.get_control_console(console_sock)

    issues, err = control_console.eval_res_err('''
        return require('cartridge.issues').list_on_cluster()
    ''')

    if err:
        helpers.warn("Received error on getting list of cluster issues: %s" % err)

    warning_issues = list(filter(lambda issue: issue['level'] == 'warning', issues))
    critical_issues = list(filter(lambda issue: issue['level'] == 'critical', issues))
    unknown_issues = list(filter(lambda issue: issue['level'] not in ['warning', 'critical'], issues))

    messages = get_messages(warning=warning_issues, critical=critical_issues, unknown=unknown_issues)
    helpers.warn(*messages)

    if issues:
        if allow_warnings:
            critical_issues_num = len(issues) - len(warning_issues)
            if critical_issues_num > 0:
                return helpers.ModuleRes(failed=True, msg="Cluster has %s critical issues" % critical_issues_num)
        else:
            return helpers.ModuleRes(failed=True, msg="Cluster has %s issues" % len(issues))

    return helpers.ModuleRes(changed=False)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, check_cluster_issues)
