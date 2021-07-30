#!/usr/bin/env python
import fnmatch
import os

from ansible.module_utils.basic import AnsibleModule

argument_spec = {
    'instance_info': {'required': True, 'type': 'dict'},
    'files_list': {'required': True, 'type': 'list'},
    'stateboard': {'required': True, 'type': 'bool'},
    'hostvars': {'required': False, 'type': 'dict'},
    'backup_files_from_machine': {'required': False, 'type': 'list'},
    'instances_from_machine': {'required': False, 'type': 'list'},
}


def glob_list_match(path, glob_list):
    for pattern in glob_list:
        norm_path = os.path.normpath(path)
        base_name = os.path.basename(path)

        if fnmatch.fnmatch(norm_path, pattern) or fnmatch.fnmatch(base_name, pattern):
            return True

    return False


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
    files_list = list(filter(
        lambda p: p == conf_path or not p.startswith(conf_path),
        map(lambda path: path.strip(os.path.sep), files_list),
    ))

    if not stateboard:
        exp_files_glob_list = [
            instance_info['conf_file'],
            instance_info['app_conf_file'],
            os.path.join(instance_info['work_dir'], ".tarantool.cookie"),
            os.path.join(instance_info['work_dir'], "config"),
            os.path.join(instance_info['memtx_dir'] or instance_info['work_dir'], "*.snap"),
            os.path.join(instance_info['vinyl_dir'] or instance_info['work_dir'], "*.vylog"),
            os.path.join(instance_info['vinyl_dir'] or instance_info['work_dir'], "*", "*", "*.index"),
            os.path.join(instance_info['vinyl_dir'] or instance_info['work_dir'], "*", "*", "*.run"),
        ]
    else:
        exp_files_glob_list = [
            instance_info['conf_file'],
            os.path.join(instance_info['memtx_dir'], "*.snap"),
        ]

    exp_files_glob_list = list(map(lambda r: r.strip(os.path.sep), exp_files_glob_list))

    if len(exp_files_glob_list) != len(files_list):
        files_list_is_ok = False
    else:
        files_list_is_ok = all([
            glob_list_match(file_path, exp_files_glob_list)
            for file_path in files_list
        ])

    if not files_list_is_ok:
        module.fail_json(msg="Received bad backup files list. Expected %s, got %s" % (
            exp_files_glob_list, files_list
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
