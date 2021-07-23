#!/usr/bin/env python

import os
import re

from ansible.module_utils.basic import AnsibleModule


argument_spec = {
    'instance_info': {'required': True, 'type': 'dict'},
    'files_list': {'required': True, 'type': 'list'},
    'stateboard': {'required': True, 'type': 'bool'},
    'hostvars': {'required': False, 'type': 'dict'},
    'backup_files_from_machine': {'required': False, 'type': 'list'},
    'instances_from_machine': {'required': False, 'type': 'list'},
}


if __name__ == '__main__':
    module = AnsibleModule(argument_spec=argument_spec)
    params = module.params

    instance_info = params['instance_info']
    files_list = params['files_list']
    stateboard = params['stateboard']
    hostvars = params['hostvars']
    backup_files_from_machine = params['backup_files_from_machine']
    instances_from_machine = params['instances_from_machine']

    # filter out config subdirectories
    conf_path = os.path.join(instance_info['work_dir'], 'config').strip(os.path.sep)
    files_list = list(sorted(filter(
        lambda p: p == conf_path or not p.startswith(conf_path),
        map(lambda path: path.strip(os.path.sep), files_list),
    )))

    if not stateboard:
        exp_files_list_regexps = [
            instance_info['conf_file'],
            instance_info['app_conf_file'],
            os.path.join(instance_info['work_dir'], "config"),
            os.path.join(instance_info['memtx_dir'], r"\d+\.snap"),
            os.path.join(instance_info['vinyl_dir'], r"\d+\.vylog"),
            os.path.join(instance_info['vinyl_dir'], r"\d+", r"\d+", r"\d+\.index"),
            os.path.join(instance_info['vinyl_dir'], r"\d+", r"\d+", r"\d+\.run"),
        ]
    else:
        exp_files_list_regexps = [
            instance_info['conf_file'],
            os.path.join(instance_info['memtx_dir'], r"\d+.snap"),
        ]

    exp_files_list_regexps = list(map(lambda r: r.strip(os.path.sep), exp_files_list_regexps))

    if len(exp_files_list_regexps) != len(files_list):
        files_list_is_ok = False
    else:
        files_list_is_ok = all([
            re.match(exp_files_list_regexps[i], file_path)
            for i, file_path in enumerate(files_list)
        ])

    if not files_list_is_ok:
        module.fail_json(msg="Received bad backup files list. Expected %s, got %s" % (
            exp_files_list_regexps, files_list
        ))

    if backup_files_from_machine is None:
        module.exit_json()

    exp_backup_files_from_machine = []
    for instance in instances_from_machine:
        exp_backup_files_from_machine += hostvars[instance]['instance_backup_files']

    if backup_files_from_machine != exp_backup_files_from_machine:
        module.fail_json(msg="Received bad list of backup files from the same machine. Expected %s, got %s" % (
            exp_backup_files_from_machine, backup_files_from_machine
        ))

    module.exit_json()
