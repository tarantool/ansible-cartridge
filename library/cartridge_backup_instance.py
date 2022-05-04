import os
import tarfile
import time

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': False, 'type': 'str'},
    'instance_id': {'required': False, 'type': 'str'},
    'stateboard': {'required': False, 'type': 'bool'},
    'backups_dir': {'required': False, 'type': 'str'},
    'instance_conf_file': {'required': False, 'type': 'str'},
    'app_conf_file': {'required': False, 'type': 'str'},
    'start_only': {'required': False, 'type': 'bool', 'default': False},
    'stop_only': {'required': False, 'type': 'bool', 'default': False},
    'custom_backup_files': {'required': False, 'type': 'list'},
}


def backup_start(control_console, params):
    stateboard = params.get('stateboard')
    assert stateboard is not None, 'Parameter "stateboard" is required'
    instance_conf_file = params.get('instance_conf_file')
    assert instance_conf_file is not None, 'Parameter "instance_conf_file" is required'
    app_conf_file = params.get('app_conf_file')
    assert app_conf_file is not None, 'Parameter "app_conf_file" is required'

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
            local work_dir_files = {
                'config',
                'config.backup',
                'config.yml',
                'config.backup.yml',
                '.tarantool.cookie',
            }
            for _, work_dir_file in ipairs(work_dir_files) do
                local work_dir_file_path = fio.pathjoin(work_dir, work_dir_file)
                if fio.path.exists(work_dir_file_path) then
                    table.insert(paths, work_dir_file_path)
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
            if os.path.exists(path):
                tar.add(path)

    return archive_path


def backup_stop(control_console):
    ok, err = control_console.eval_res_err('''
        return pcall(box.backup.stop)
    ''')

    if not ok:
        return err

    return None


def custom_backup(params):
    custom_backup_files = params.get('custom_backup_files')
    assert custom_backup_files is not None, 'Parameter "custom_backup_files" is required'

    # ARCHIVE
    instance_id = params.get('instance_id')
    assert instance_id is not None, 'Parameter "instance_id" is required'
    backups_dir = params.get('backups_dir')
    assert backups_dir is not None, 'Parameter "backups_dir" is required'
    backup_archive_path = backup_pack(instance_id, backups_dir, custom_backup_files)

    return helpers.ModuleRes(changed=True, fact={
        'backup_archive_path': backup_archive_path,
        'backup_files': custom_backup_files,
    })


def tnt_backup(params):
    start_only = params.get('start_only', False)
    stop_only = params.get('stop_only', False)

    assert not (start_only and stop_only), "impossible to use 'start_only' with 'stop_only'"

    console_sock = params.get('console_sock')
    assert console_sock is not None, 'Parameter "console_sock" is required'
    control_console = helpers.get_control_console(console_sock)

    if not helpers.box_cfg_was_called(control_console):
        return helpers.ModuleRes(failed=True, msg="box.cfg wasn't called yet")

    # STOP ONLY
    if stop_only:
        err = backup_stop(control_console)
        if err is not None:
            return helpers.ModuleRes(failed=True, msg="Failed to stop backup: %s" % err)

        return helpers.ModuleRes(changed=True)

    # START
    backup_files, err = backup_start(control_console, params)
    if err is not None:
        return helpers.ModuleRes(failed=True, msg="Failed to start backup: %s" % err)

    if start_only:
        return helpers.ModuleRes(changed=True, fact={
            'backup_files': backup_files,
        })

    # ARCHIVE
    instance_id = params.get('instance_id')
    assert instance_id is not None, 'Parameter "instance_id" is required'
    backups_dir = params.get('backups_dir')
    assert backups_dir is not None, 'Parameter "backups_dir" is required'
    backup_archive_path = backup_pack(instance_id, backups_dir, backup_files)

    # STOP
    err = backup_stop(control_console)
    if err is not None:
        return helpers.ModuleRes(failed=True, msg="Failed to stop backup: %s" % err)

    return helpers.ModuleRes(changed=True, fact={
        'backup_archive_path': backup_archive_path,
        'backup_files': backup_files,
    })


def call_backup(params):
    if params.get('custom_backup_files'):
        return custom_backup(params)
    else:
        return tnt_backup(params)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, call_backup)
