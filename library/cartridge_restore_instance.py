import os
import shutil
import tarfile

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'console_sock': {'required': True, 'type': 'str'},
    'restore_archive_path': {'required': False, 'type': 'str'},
    'remote_backups_dir': {'required': False, 'type': 'str'},
    'instance_id': {'required': False, 'type': 'str'},
    'force_restore': {'required': False, 'type': 'bool', 'default': True},
}


#############################
# Conflicting files getters #
#############################


def get_tgz_conflicting_files(archive_path):
    with tarfile.open(archive_path, 'r:gz') as tar:
        conflicting_files = []

        for src_member in tar.getmembers():
            full_dst = os.path.join('/', src_member.name)

            if src_member.isdir() or not os.path.exists(full_dst):
                continue

            if os.stat(full_dst).st_size != src_member.size:
                conflicting_files.append(full_dst)

    return conflicting_files


def get_folder_conflicting_files(archive_path):
    conflicting_files = []

    for root, _, files in os.walk(archive_path):
        for src in files:
            full_src = os.path.join(root, src)
            full_dst = os.path.join('/', os.path.relpath(full_src, archive_path))

            if not os.path.exists(full_dst):
                continue

            if os.stat(full_src).st_size != os.stat(full_dst).st_size:
                conflicting_files.append(full_dst)

    return conflicting_files


####################
# Unpack functions #
####################


def unpack_tgz(archive_path):
    with tarfile.open(archive_path, 'r:gz') as tar:
        tar.extractall('/')

    return True, None


def move_files(archive_path):
    for root, dirs, files in os.walk(archive_path):
        for src in dirs:
            full_src = os.path.join(root, src)
            full_dst = os.path.join('/', os.path.relpath(full_src, archive_path))

            if os.path.exists(full_dst):
                continue

            os.makedirs(full_dst, os.stat(full_src).st_mode)

        for src in files:
            full_src = os.path.join(root, src)
            full_dst = os.path.join('/', os.path.relpath(full_src, archive_path))

            if os.path.exists(full_dst):
                os.remove(full_dst)

            if os.path.islink(full_src):
                os.symlink(os.readlink(full_src), full_dst)
            else:
                shutil.copy(full_src, full_dst)

    return True, None


####################
# Common functions #
####################


def get_archive_path(restore_archive_path, remote_backups_dir, instance_id):
    if restore_archive_path:
        if not os.path.exists(restore_archive_path):
            return None, (
                "Backup '%s' not found. "
                "Specify another path to backup (by 'cartridge_restore_archive_path') or "
                "keep empty to find backup in folder with backups." % restore_archive_path
            )
        return restore_archive_path, None

    if not os.path.exists(remote_backups_dir):
        return None, (
            "Folder with backups (%s) not found."
            "Specify path to backup (by 'cartridge_restore_archive_path') or "
            "another path to folder with backups (by 'remote_backups_dir')." % remote_backups_dir
        )

    for path in sorted(os.listdir(remote_backups_dir), reverse=True):
        full_path = os.path.join(remote_backups_dir, path)

        if not os.path.isfile(full_path):
            continue

        if instance_id in full_path:
            helpers.warn("Backup '%s' was selected from folder with backups to restore instance" % full_path)
            return full_path, None

    return None, (
        "Impossible to find backup of current instance in folder with backups (%s). "
        "Specify path to backup (by 'cartridge_restore_archive_path') or "
        "another path to folder with backups (by 'remote_backups_dir')." % remote_backups_dir
    )


def get_specific_format_funcs(archive_path):
    if os.path.isdir(archive_path):
        return get_folder_conflicting_files, move_files, None
    elif archive_path.endswith('.tar.gz'):
        return get_tgz_conflicting_files, unpack_tgz, None

    return None, None, 'Unknown format of backup, supported formats: TGZ, folder.'


def restore_archive(archive_path, force_restore):
    get_conflicting_files_func, unpack_func, err = get_specific_format_funcs(archive_path)
    if err:
        return None, err

    conflicting_files = get_conflicting_files_func(archive_path)
    if conflicting_files:
        msg = "Some files already exist and have a different size than in the archive: %s. "
        msg %= ', '.join(conflicting_files)
        if force_restore:
            msg += "They have been overwritten."
            helpers.warn(msg)
        else:
            msg += "Remove them or set 'cartridge_force_restore' flag to overwrite."
            return None, msg

    return unpack_func(archive_path)


def call_restore(params):
    if helpers.is_instance_running(params['console_sock']):
        return helpers.ModuleRes(failed=True, msg="instance shouldn't be running")

    archive_path, err = get_archive_path(
        params['restore_archive_path'],
        params['remote_backups_dir'],
        params['instance_id'],
    )
    if err:
        return helpers.ModuleRes(failed=True, msg=err)

    changed, err = restore_archive(archive_path, params['force_restore'])
    if err:
        return helpers.ModuleRes(failed=True, msg=err)

    return helpers.ModuleRes(changed=changed)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, call_restore)
