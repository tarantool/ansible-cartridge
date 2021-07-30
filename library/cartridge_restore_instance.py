import grp
import hashlib
import os
import pwd
import re
import shutil
import tarfile

from ansible.module_utils.helpers import Helpers as helpers

argument_spec = {
    'instance_info': {'required': True, 'type': 'dict'},
    'app_user': {'required': True, 'type': 'str'},
    'app_group': {'required': True, 'type': 'str'},
    'paths_to_keep_before_restore': {'required': False, 'type': 'list', 'default': []},
    'restore_backup_path': {'required': False, 'type': 'str'},
    'remote_backups_dir': {'required': False, 'type': 'str'},
    'force_restore': {'required': False, 'type': 'bool', 'default': False},
    'allow_alien_backups': {'required': False, 'type': 'bool', 'default': False},
    'skip_cleanup_on_restore': {'required': False, 'type': 'bool', 'default': False},
}


###########
# Helpers #
###########

def make_dirs(path, uid, gid, mode=0o755):
    if os.path.exists(path):
        return

    path = path.rstrip(os.path.sep)

    head, tail = os.path.split(path)
    if not tail:
        head, tail = os.path.split(head)

    if head and tail:
        make_dirs(head, uid, gid, mode)

    os.mkdir(path, mode)
    os.chown(path, uid, gid)


def md5_buffer(fd):
    hash_md5 = hashlib.md5()
    for chunk in iter(lambda: fd.read(4096), b""):
        hash_md5.update(chunk)
    fd.close()
    return hash_md5.hexdigest()


def is_path_of_instance(path, instance_id):
    # Expected one of variant:
    # /opt/backups/myapp.i-1.tar.gz
    # /opt/backups/myapp.i-1.2020-01-01.tar.gz
    # /opt/backups/myapp.i-1.2020-01-01-010101.tar.gz
    # /opt/backups/myapp.i-1.1627650508.tar.gz
    # /opt/backups/backup.myapp.i-1.tar.gz
    # /opt/backups/myapp.i-1/
    # ...
    instance_id = instance_id.replace(".", r"\.")
    path = path.strip(os.path.sep)
    m = re.search(r'%s(\W(\d{4}\W\d{2}\W\d{2}(\W\d{6})?|\d{6,}))?(.tar.gz|/|$)' % instance_id, path, re.I | re.U)
    return m is not None


#############################
# Conflicting files getters #
#############################


def is_path_to_remove(path, paths_to_remove, paths_to_keep, skip_cleanup_on_restore):
    if skip_cleanup_on_restore:
        return False

    if helpers.glob_list_match(path, paths_to_keep):
        return False

    for path_to_remove in paths_to_remove:
        if path.startswith(path_to_remove):
            return True

    return False


def get_tgz_conflicting_files(backup_path, ignore_func, instance_id):
    conflicting_files = []
    is_backup_of_correct_instance = False

    with tarfile.open(backup_path, 'r:gz') as tar:
        for src_member in tar.getmembers():
            full_dst = os.path.join('/', src_member.name)

            if is_path_of_instance(full_dst, instance_id):
                is_backup_of_correct_instance = True

            if src_member.isdir() or not os.path.exists(full_dst):
                continue

            if ignore_func(full_dst):
                continue

            src_md5 = md5_buffer(tar.extractfile(src_member))
            dst_md5 = md5_buffer(open(full_dst, "rb"))
            if src_md5 != dst_md5:
                conflicting_files.append(full_dst)

    return conflicting_files, is_backup_of_correct_instance


def get_dir_conflicting_files(backup_path, ignore_func, instance_id):
    conflicting_files = []
    is_backup_of_correct_instance = False

    for root, _, files in os.walk(backup_path):
        for src in files:
            full_src = os.path.join(root, src)
            full_dst = os.path.join('/', os.path.relpath(full_src, backup_path))

            if is_path_of_instance(full_dst, instance_id):
                is_backup_of_correct_instance = True

            if not os.path.exists(full_dst):
                continue

            if ignore_func(full_dst):
                continue

            src_md5 = md5_buffer(open(full_src, "rb"))
            dst_md5 = md5_buffer(open(full_dst, "rb"))
            if src_md5 != dst_md5:
                conflicting_files.append(full_dst)

    return conflicting_files, is_backup_of_correct_instance


####################
# Unpack functions #
####################


def unpack_tgz(backup_path, uid, gid):
    with tarfile.open(backup_path, 'r:gz') as tar:
        for src_member in tar.getmembers():
            dir_path = os.path.dirname(os.path.join('/', src_member.name))
            make_dirs(dir_path, uid, gid)

        tar.extractall('/')

    return True, None


def move_files(backup_path, uid, gid):
    for root, dirs, files in os.walk(backup_path):
        for src in dirs:
            full_src = os.path.join(root, src)
            full_dst = os.path.join('/', os.path.relpath(full_src, backup_path))

            if os.path.exists(full_dst):
                continue

            src_stat = os.stat(full_src)
            make_dirs(full_dst, uid, gid, src_stat.st_mode)

        for src in files:
            full_src = os.path.join(root, src)
            full_dst = os.path.join('/', os.path.relpath(full_src, backup_path))

            if os.path.exists(full_dst):
                os.remove(full_dst)

            if os.path.islink(full_src):
                os.symlink(os.readlink(full_src), full_dst)
            else:
                shutil.copy(full_src, full_dst)

            os.chown(full_dst, uid, gid)

    return True, None


####################
# Common functions #
####################


def get_backup_path(restore_backup_path, remote_backups_dir, instance_id):
    if restore_backup_path:
        if not os.path.exists(restore_backup_path):
            return None, (
                "Backup '%s' not found. "
                "Specify another path to backup (by 'cartridge_restore_backup_path') or "
                "keep empty to find backup in directory with backups ('remote_backups_dir')." % restore_backup_path
            )
        return restore_backup_path, None

    if not os.path.exists(remote_backups_dir):
        return None, (
            "Directory with backups (%s) not found."
            "Specify path to backup (by 'cartridge_restore_backup_path') or "
            "another path to directory with backups (by 'remote_backups_dir')." % remote_backups_dir
        )

    for path in sorted(os.listdir(remote_backups_dir), reverse=True):
        full_path = os.path.join(remote_backups_dir, path)

        if not os.path.isfile(full_path):
            continue

        if is_path_of_instance(full_path, instance_id):
            helpers.warn("Backup '%s' from directory with backups is used to restore instance" % full_path)
            return full_path, None

    return None, (
        "Impossible to find backup of current instance in directory with backups (%s). "
        "Specify path to backup (by 'cartridge_restore_backup_path') or "
        "another path to directory with backups (by 'remote_backups_dir')." % remote_backups_dir
    )


def get_specific_format_funcs(backup_path):
    if os.path.isdir(backup_path):
        return get_dir_conflicting_files, move_files, None
    elif backup_path.endswith('.tar.gz'):
        return get_tgz_conflicting_files, unpack_tgz, None

    return None, None, 'Unknown format of backup, supported formats: TGZ, directory.'


def cleanup_files(paths_to_remove, paths_to_keep):
    for path_to_remove in paths_to_remove:
        if not os.path.exists(path_to_remove) or helpers.glob_list_match(path_to_remove, paths_to_keep):
            continue

        if os.path.isdir(path_to_remove):
            shutil.rmtree(path_to_remove)
        else:
            os.remove(path_to_remove)


def restore_archive(
    backup_path,
    instance_id,
    paths_to_remove,
    paths_to_keep,
    force_restore,
    allow_alien_backups,
    skip_cleanup_on_restore,
    app_user,
    app_group,
):
    paths_to_keep = paths_to_keep + ['.tarantool.cookie']

    get_conflicting_files_func, unpack_func, err = get_specific_format_funcs(backup_path)
    if err:
        return None, err

    conflicting_files, is_backup_of_correct_instance = get_conflicting_files_func(
        backup_path,
        lambda path: is_path_to_remove(path, paths_to_remove, paths_to_keep, skip_cleanup_on_restore),
        instance_id,
    )

    if not is_backup_of_correct_instance:
        msg = "Seems that selected backup of another instance. "
        if allow_alien_backups:
            msg += "This error ignored, because the 'cartridge_allow_alien_backups' flag is set."
            helpers.warn(msg)
        else:
            msg += "If you are sure that this backup is correct, set 'cartridge_allow_alien_backups' flag."
            return None, msg

    if conflicting_files:
        msg = "Some files already exist and have a different md5 sum than in the backup: %s. "
        msg %= ', '.join(conflicting_files)
        if force_restore:
            msg += "They have been overwritten, because the 'cartridge_force_restore' flag is set."
            helpers.warn(msg)
        else:
            msg += "Remove them or set 'cartridge_force_restore' flag to overwrite."
            return None, msg

    if not skip_cleanup_on_restore:
        cleanup_files(paths_to_remove, paths_to_keep)

    uid = pwd.getpwnam(app_user).pw_uid
    gid = grp.getgrnam(app_group).gr_gid

    return unpack_func(backup_path, uid, gid)


def call_restore(params):
    instance_info = params['instance_info']

    if helpers.is_instance_running(instance_info['console_sock']):
        return helpers.ModuleRes(failed=True, msg="instance shouldn't be running")

    backup_path, err = get_backup_path(
        params['restore_backup_path'],
        params['remote_backups_dir'],
        instance_info['instance_id'],
    )
    if err:
        return helpers.ModuleRes(failed=True, msg=err)

    changed, err = restore_archive(
        backup_path,
        instance_info['instance_id'],
        instance_info['paths_to_remove_on_expel'],
        params['paths_to_keep_before_restore'],
        params['force_restore'],
        params['allow_alien_backups'],
        params['skip_cleanup_on_restore'],
        params['app_user'],
        params['app_group'],
    )
    if err:
        return helpers.ModuleRes(failed=True, msg=err)

    return helpers.ModuleRes(changed=changed)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, call_restore)
