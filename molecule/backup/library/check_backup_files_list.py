#!/usr/bin/env python

import os
import re

from ansible.module_utils.basic import AnsibleModule


argument_spec = {
    'instance_info': {'required': True, 'type': 'dict'},
    'files_list': {'required': True, 'type': 'list'},
    'stateboard': {'required': True, 'type': 'bool'},
}


if __name__ == '__main__':
    module = AnsibleModule(argument_spec=argument_spec)
    params = module.params

    files_list = params['files_list']
    instance_info = params['instance_info']
    stateboard = params['stateboard']

    files_list = [
        path.strip("/") for path in files_list
    ]

    # filter out config subdirectories
    conf_path = os.path.join(instance_info['work_dir'], 'config').strip("/")
    files_list = list(filter(
        lambda p: p == conf_path or not p.startswith(conf_path),
        files_list,
    ))

    if not stateboard:
        exp_files_list_regexps = [
            os.path.join(instance_info['memtx_dir'], r"\d+.snap"),
            os.path.join(instance_info['vinyl_dir'], r"\d+.vylog"),
            os.path.join(instance_info['work_dir'], "config"),
            instance_info['conf_file'],
            instance_info['app_conf_file'],
        ]
    else:
        exp_files_list_regexps = [
            os.path.join(instance_info['memtx_dir'], r"\d+.snap"),
            instance_info['conf_file'],
        ]

    exp_files_list_regexps = [
        r.strip("/") for r in exp_files_list_regexps
    ]

    files_list_is_ok = all([
        re.match(exp_files_list_regexps[i], file_path)
        for i, file_path in enumerate(files_list)
    ])

    if not files_list_is_ok:
        module.fail_json(msg="Received bad backup files list. Expected %s, got %s" % (
            exp_files_list_regexps, files_list
        ))

    module.exit_json(
        files_list=files_list,
        exp_files_list_regexps=exp_files_list_regexps
    )
