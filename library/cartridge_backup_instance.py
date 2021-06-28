import time
import tarfile
import os

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'instance_id': {'required': False, 'type': 'str'},
    'stateboard': {'required': False, 'type': 'bool'},
    'backups_dir': {'required': False, 'type': 'str'},
    'instance_conf_file': {'required': False, 'type': 'str'},
    'app_conf_file': {'required': False, 'type': 'str'},

    'start_only': {'required': False, 'type': 'bool', 'default': False},
    'stop_only': {'required': False, 'type': 'bool', 'default': False},
}


def backup_start(control_console, params):
    stateboard = params['stateboard']
    instance_conf_file = params['instance_conf_file']
    app_conf_file = params['app_conf_file']

    # create snapshot and start a backup
    backup_files, err = control_console.eval_res_err('''
        local fun = require('fun')
        local fio = require('fio')
        local confapplier = require('cartridge.confapplier')

        local is_stateboard = ...

        local ok, err = pcall(box.snapshot)
        if not ok then
            return nil, string.format("Failed to create data snapshot: %s", err)
        end

        local ok, paths = pcall(box.backup.start)
        if not ok then
            return nil, string.format("Failed to start backup: %s", paths)
        end

        paths = fun.map(function(path) return fio.abspath(path) end, paths):totable()

        if not is_stateboard then
            local work_dir = confapplier.get_workdir()
            local config_names = {'config', 'config.backup', 'config.yml', 'config.backup.yml'}
            for _, config_name in ipairs(config_names) do
                local config_path = fio.pathjoin(work_dir, config_name)
                if fio.path.exists(config_path) then
                    table.insert(paths, config_path)
                end
            end
        end

        return paths
    ''', stateboard)

    if err is not None:
        return None, err

    backup_files.append(instance_conf_file)
    if not stateboard:
        backup_files.append(app_conf_file)

    return backup_files, None


def backup_pack(instance_id, backups_dir, backup_files):
    archive_name = "{instance_id}.{time}.tar.gz".format(
        instance_id=instance_id,
        time=time.strftime("%Y-%m-%d-%H%M%S")
    )
    archive_path = os.path.join(backups_dir, archive_name)

    with tarfile.open(archive_path, "w:gz") as tar:
        for path in backup_files:
            tar.add(path)

    return archive_path


def backup_stop(control_console):
    ok, err = control_console.eval_res_err('''
        return pcall(box.backup.stop)
    ''')

    if not ok:
        return err

    return None


def call_backup(params):
    start_only = params['start_only']
    stop_only = params['stop_only']

    assert not(start_only and stop_only), "impossible to use 'start_only' with 'stop_only'"

    console_sock = params['console_sock']
    control_console = helpers.get_control_console(console_sock)

    if not helpers.box_cfg_was_called(control_console):
        return helpers.ModuleRes(failed=True, msg="box.cfg wasn't called yet")

    backup_files = None
    backup_archive_path = None

    # START
    if not stop_only:
        backup_files, err = backup_start(control_console, params)
        if err is not None:
            return helpers.ModuleRes(failed=True, msg=err)

    if start_only:
        return helpers.ModuleRes(failed=False, changed=True, fact={
            'backup_files': backup_files,
        })

    # ARCHIVE
    if not stop_only:
        instance_id = params['instance_id']
        backups_dir = params['backups_dir']
        backup_archive_path = backup_pack(instance_id, backups_dir, backup_files)

    # STOP
    err = backup_stop(control_console)
    if err is not None:
        if stop_only:
            return helpers.ModuleRes(failed=True, msg=err)
        helpers.warn("Failed to stop backup: %s" % err)

    return helpers.ModuleRes(failed=False, changed=True, fact={
        'backup_archive_path': backup_archive_path,
        'backup_files': backup_files,
    })


if __name__ == '__main__':
    helpers.execute_module(argument_spec, call_backup)
