# Backups

The role allows creating a backup archive for each application instance and stateboard.
The instance backup process contains three stages:

* Starting backup:
  * [`box.snapshot()`](https://www.tarantool.io/en/doc/latest/reference/reference_lua/box_snapshot/) is called;
  * [`box.backup.start()`](https://www.tarantool.io/en/doc/latest/reference/reference_lua/box_backup/start/) is called;
  * `instance_backup_files` variable is set ([list of instance files](#instance-files) to back up);
  * `backup_files_from_machine` variable is set (list of files to back up for
    all instances on the same machine as a current one);
* Creating and fetching the backup archive:
  * all backup files are packed into the TGZ archive placed in [`cartridge_remote_backups_dir`](/doc/variables.md#backups-configuration);
  * all paths inside the archive are relative to `/`;
  * `backup_archive_path` variable is set (path to the instance backup archive on the remote machine);
  * fetching an archive from the remote machine to
    [`cartridge_fetch_backups_dir`](/doc/variables.md#backups-configuration)
    if [`cartridge_fetch_backups`](/doc/variables.md#backups-configuration) is `true`;
  * `fetched_backup_archive_path` is set if [`cartridge_fetch_backups`](/doc/variables.md#backups-configuration)
    is `true` (path to the fetched instance backup archive on the local machine);
* Stopping backup:
  * [`box.backup.stop()`](https://www.tarantool.io/en/doc/latest/reference/reference_lua/box_backup/stop/) is called.

**Note**, that application instance should be joined to cluster for performing backup.

There are three steps that allows to create a backup:

* [`backup`](/doc/steps.md#step-backup) - performs all three stages;
* [`backup_start`](/doc/steps.md#step-backup_start) - only starts backup;
* [`backup_stop`](/doc/steps.md#step-backup_stop) - only stops backup.

## Instance files

These files are added to an archive for each instance (excluding the stateboard):

* snapshot and vinyl files returned by
  [`box.backup.start()`](https://www.tarantool.io/en/doc/latest/reference/reference_lua/box_backup/start/);
* cluster-wide config and its backup;
* instance configuration file;
* application configuration file.

For a stateboard instance only snapshot files and instance configuration file will be added.

## How to use backup steps?

* `backup` step can be used for performing all three backup stages, see [example](#using-backup-step);
* `backup_start` + `backup_stop` steps can be used to perform some custom actions
  with instance files list, see [example](#using-backup_start-and-backup_stop).

## How to restore from saved backup?

To restore you can use the `restore` step. It contains three stages:

* find TGZ backup or directory with backup ([details here](#find-backup));
* check for conflicting files ([details here](#check-for-conflicting-files));
* replace current files with files from backup ([details here](#replace-current-files-with-files-from-backup)).

Examples of restoring from backup, you can see [below](#using-restore-step).

### Find backup

1. You can pass path to backup by `cartridge_restore_backup_path` variable.
   Path to a TGZ archive or a directory with backup can be specified.
2. If `cartridge_restore_backup_path` variable is omitted, the role
   will look in the `cartridge_remote_backups_dir` directory
   (by default `/opt/tarantool/backups`) for the backup
   whose name contains the instance ID and is the latest alphabetically (with the latest date).
3. If not found any file or directory backup that belongs to given instance, an error will occur.

You can see examples of using the described variables [below](#using-restore-step).

### Check for conflicting files

After selecting a backup, `restore` step checks the following:
- files in the selected backup do not conflict with files in the system,
  taking into account that some files will be deleted
  (in order to overwrite such files, set the `cartridge_force_restore` flag);
- probably the selected backup belongs to the instance that is currently being
  restored (in order to allow recovery from such backup, set the
  `cartridge_allow_alien_backup` flag).

You can see examples of using the described variables [below](#using-restore-step).

### Replace current files with files from backup

After all checks have been passed, step make two actions:
1. If `cartridge_skip_cleanup_on_restore` is not set, step deletes the instance
   files that are in the system (except for `.tarantool.cookie` and files that
   match the templates from `cartridge_paths_to_keep_before_restore` list);
2. Step unpacks files from selected backup.

You can see examples of using the described variables [below](#using-restore-step).

## Examples

### Using `backup` step

[`backup`](/doc/steps.md#step-backup) step performs all backup stages:

* starting backup;
* creating and fetching the backup archive;
* stopping backup.

It can be used to create backup archive for each instance and fetch all archives on local machine:

```yaml
- name: 'Create and fetch all instances backups'
  hosts: cluster
  become: true
  become_user: root
  gather_facts: false
  tasks:
    - name: 'Backup'
      import_role:
        name: tarantool.cartridge
      vars:
        cartridge_scenario:
          - backup
        cartridge_fetch_backups: true
        cartridge_fetch_backups_dir: ./my_backups
```

After running this playbook, we have such archive on local machine:

```bash
├── playbook.yml
└── my_backups
    ├── myapp-stateboard.2021-07-09-133438.tar.gz
    ├── myapp.instance-1.2021-07-09-133438.tar.gz
    └── myapp.instance-2.2021-07-09-133438.tar.gz
```

On the remote machines, backups are placed in `/opt/tarantool/backups/` directory.

On each instance the following variables will be set:

- my-stateboard:

  ```json
  {
      "instance_backup_files": [
          "/opt/memtx/myapp-stateboard/00000000000000000049.snap",
          "/opt/conf.d/myapp-stateboard.yml"
      ],
      "backup_archive_path": "/opt/tarantool/backups/myapp-stateboard.2021-07-09-133438.tar.gz",
      "fetched_backup_archive_path": "/path/to/playbook/my_backups/myapp-stateboard.2021-07-09-133438.tar.gz"
  }
  ```

- instance-1:

  ```json
  {
      "instance_backup_files": [
          "/opt/memtx/myapp.instance-1/00000000000000000008.snap",
          "/opt/vinyl/myapp.instance-1/00000000000000000000.vylog",
          "/opt/data/myapp.instance-1/config",
          "/opt/conf.d/myapp.instance-1.yml",
          "/opt/conf.d/myapp.yml"
      ],
      "backup_archive_path": "/opt/tarantool/backups/myapp.instance-1.2021-07-09-133438.tar.gz",
      "fetched_backup_archive_path": "/path/to/playbook/my_backups/myapp.instance-1.2021-07-09-133438.tar.gz"
  }
  ```

- ...

### Using `backup_start` and `backup_stop`

Let's imagine that we want to archive backup files not for each instance, but for each machine:

* use [`backup_start`](/doc/steps.md#step-backup_start) for backup staring;
* use [`backup_files_from_machine`](/doc/steps.md#step-backup_start)
  and [`single_instances_for_each_machine`](/doc/steps.md#role-variables-descriptions)
  to archive files for each machine;
* use [`backup_stop`](/doc/steps.md#step-backup_stop) to stop backup process.

```yaml
- name: 'Archive all instances files on machine'
  hosts: cluster
  become: true
  become_user: root
  gather_facts: false
  tasks:
    - name: 'Create backups dir'
      file:
        path: '/opt/tarantool/backups'
        owner: '{{ cartridge_app_user }}'
        group: '{{ cartridge_app_group }}'
        state: directory
        mode: 0750

    - name: 'Start backup'
      import_role:
        name: ansible-cartridge
      vars:
        cartridge_scenario:
          - backup_start

    - name: 'Create archives with backups by machines'
      archive:
        dest: /opt/tarantool/backups/{{ cartridge_app_name }}.{{ ansible_host }}.tar.gz
        path: '{{ backup_files_from_machine }}'
      when: inventory_hostname in single_instances_for_each_machine

    - name: 'Stop backup'
      import_role:
        name: ansible-cartridge
      vars:
        cartridge_scenario:
          - backup_stop
```

I will produce such archives:

```
[root@vm1 /]# tar -ztf /opt/tarantool/backups/myapp.vm1.tar.gz
memtx/myapp.instance-1/00000000000000000004.snap
data/myapp.instance-1/config/auth.yml
data/myapp.instance-1/config/vshard_groups.yml
data/myapp.instance-1/config/topology.yml
conf.d/myapp.instance-1.yml
conf.d/myapp.yml
memtx/myapp-stateboard/00000000000000000049.snap
conf.d/myapp-stateboard.yml

[root@vm2 /]# tar -ztf /opt/tarantool/backups/myapp.vm2.tar.gz
memtx/myapp.instance-2/00000000000000000004.snap
data/myapp.instance-2/config/auth.yml
data/myapp.instance-2/config/vshard_groups.yml
data/myapp.instance-2/config/topology.yml
conf.d/myapp.instance-2.yml
conf.d/myapp.yml
```

### Using `restore` step

If you want to restore an instance from the latest TGZ backup
from `cartridge_remote_backups_dir`, just run restore step:

```yaml
- name: 'Restore instance-1 from latest backup'
  hosts: instance-1
  become: true
  become_user: root
  gather_facts: false
  tasks:
    - name: 'Restore'
      import_role:
        name: tarantool.cartridge
      vars:
        cartridge_scenario:
          - restore
```

You can select backup manually by `cartridge_restore_backup_path` variable:

```yaml
- name: 'Restore instance-1 from selected backup'
  hosts: instance-1
  become: true
  become_user: root
  gather_facts: false
  tasks:
    - name: 'Restore'
      import_role:
        name: tarantool.cartridge
      vars:
        cartridge_restore_backup_path: '/opt/tarantool/backups/myapp.instance-1.2021-07-09-133438/'
        cartridge_scenario:
          - restore
```

By default, only `.tarantool.cookie` will be kept in working directory.
If you want to keep some more files, you can put in `cartridge_paths_to_keep_before_restore`
variable some bash patterns:

```yaml
- name: 'Restore instance-1, but keep clusterwide config and logs'
  hosts: instance-1
  become: true
  become_user: root
  gather_facts: false
  tasks:
    - name: 'Restore'
      import_role:
        name: tarantool.cartridge
      vars:
        cartridge_paths_to_keep_before_restore:
          - 'config'
          - '*.log'
        cartridge_scenario:
          - restore
```

If application config was changed, but you want to replace it with config
from backup, you should set `cartridge_force_restore` flag.

```yaml
- name: 'Restore instance-1 with application config replacement'
  hosts: instance-1
  become: true
  become_user: root
  gather_facts: false
  tasks:
    - name: 'Restore'
      import_role:
        name: tarantool.cartridge
      vars:
        cartridge_force_restore: true
        cartridge_scenario:
          - restore
```
