#!/usr/bin/env python

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'show_issues': {'required': True, 'type': 'bool'},
    'allow_warnings': {'required': True, 'type': 'bool'},
    'console_sock': {'required': True, 'type': 'str'},
}


def get_messages(issues_by_level):
    messages = []
    for level, issues in sorted(issues_by_level.items()):
        if not issues:
            continue

        messages += ['* Issues (%s): '.ljust(60, "*") % level]
        messages += [issue['message'] for issue in issues]

    return messages


def check_cluster_issues(params):
    allow_warnings = params['allow_warnings']
    show_issues = params['show_issues']
    console_sock = params['console_sock']

    control_console = helpers.get_control_console(console_sock)

    issues, err = control_console.eval_res_err('''
        return require('cartridge.issues').list_on_cluster()
    ''')

    if err is not None:
        msg = "Received error on getting list of cluster issues: %s" % err
        if issues is None:
            return helpers.ModuleRes(failed=True, msg=msg)

        helpers.warn(msg)

    issues_by_level = {}
    for issue in issues:
        level = issue['level']
        if level not in issues_by_level:
            issues_by_level[level] = []

        issues_by_level[level].append(issue)

    if show_issues:
        messages = get_messages(issues_by_level)
        helpers.warn(*messages)

    if issues:
        if allow_warnings:
            critical_issues_num = len(issues) - len(issues_by_level.get('warning', []))
            if critical_issues_num > 0:
                return helpers.ModuleRes(failed=True, msg="Cluster has %s critical issues" % critical_issues_num)
        else:
            return helpers.ModuleRes(failed=True, msg="Cluster has %s issues" % len(issues))

    return helpers.ModuleRes(changed=False)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, check_cluster_issues)
