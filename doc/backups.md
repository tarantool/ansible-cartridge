# Backups

The role allows creating a backup archive for each application instance and stateboard.
The instance backup process contains three stages:

* Starting backup:
  * [`box.snapshot()`](https://www.tarantool.io/en/doc/latest/reference/reference_lua/box_snapshot/) is called;
  * [`box.backup.start()`](https://www.tarantool.io/en/doc/latest/reference/reference_lua/box_backup/start/) is called;
  * `instance_backup_files` variable is set ([list of instance files](#instance-files) to back up);
* Creating and fetching the backup archive:
  * all backup files are packed into the TGZ archive placed in [`cartridge_remote_backups_dir`](/doc/variables.md#backups-configuration);
  * all paths inside the archive are relative to `/`;
  * `backup_archive_path` variable is set (path to the instance backup archive on the remote machine);
  * fetching an archive from the remote machine to
    [`cartridge_fetch_backups_dir`](/doc/variables.md#backups-configuration)
    if [`cartridge_fetch_backups`](/doc/variables.md#backups-configuration) is `true`;
  * `fetched_backup_archive_path` is set (path to the fetched instance backup archive on the local machine);
* Stopping backup:
  * [`box.backup.stop()`](https://www.tarantool.io/en/doc/latest/reference/reference_lua/box_backup/stop/) is called.

**Note**, that application instance should be joined to cluster for performing backup.

There are three steps that allows to create a backup:

* [`backup`](/doc/scenario.md#backup) - performs all three stages;
* [`backup_start`](/doc/scenario.md#backup_start) - only starts backup;
* [`backup_stop`](/doc/scenario.md#backup_stop) - only stops backup.

## Instance files

These files are added to an archive for each instance:

* snapshot and vinyl files returned by [`box.backup.start()`](https://www.tarantool.io/en/doc/latest/reference/reference_lua/box_backup/start/);
* cluster-wide config and its backup;
* instance configuration file;
* application configuration file.

For a stateboard instance only snapshot files and configuration file will be added.

## How to use backup steps?

* `backup` step can be used for performing all three backup stages, see [example](#using-backup-step);
* `backup_start` + `backup_stop` steps can be used to perform some custom actions with instance files list, see [example](#using-backup_start-and-backup_stop).

## Examples

### Using `backup` step

[`backup`](/doc/scenario.md#backup) step performs all backup stages:

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

On the remote machines, backups are placed in `/opt/backups/` directory.

On each instance the following variables will be set:

```json
instance-1: {
    "instance_backup_files": [
        "/opt/memtx/myapp.instance-1/00000000000000000008.snap",
        "/opt/vinyl/myapp.instance-1/00000000000000000000.vylog",
        "/opt/data/myapp.instance-1/config",
        "/opt/conf.d/myapp.instance-1.yml",
        "/opt/conf.d/myapp.yml"
    ],
    "backup_archive_path": "/opt/backups/myapp.instance-1.2021-07-09-133438.tar.gz",
    "fetched_backup_archive_path": "/path/to/playbook/my_backups/myapp.instance-1.2021-07-09-133438.tar.gz"
}

my-stateboard: {
    "instance_backup_files": [
        "/opt/memtx/myapp-stateboard/00000000000000000049.snap",
        "/opt/conf.d/myapp-stateboard.yml"
    ],
    "backup_archive_path": "/opt/backups/myapp-stateboard.2021-07-09-133438.tar.gz",
    "fetched_backup_archive_path": "/path/to/playbook/my_backups/myapp-stateboard.2021-07-09-133438.tar.gz"
}

...
```

### Using `backup_start` and `backup_stop`

Let's imagine that we want to archive backup files not for each instance, but for each machine:

* use [`backup_start`](/doc/scenario.md#backup_start) for backup staring;
* collect list of backup files for each machine using `instance_backup_files` that was set for each instance;
* use [`backup_stop`](/doc/scenario.md#backup_stop) to stop backup process.

```yaml
- name: 'Archive all instances files on machine'
  hosts: cluster
  become: true
  become_user: root
  gather_facts: false
  tasks:
    - name: 'Create backups dir'
      file:
        path: '/opt/backups'
        owner: '{{ cartridge_app_user }}'
        group: '{{ cartridge_app_group }}'
        state: directory
        mode: 0660

    - name: 'Start backup'
      import_role:
        name: ansible-cartridge
      vars:
        cartridge_scenario:
          - backup_start

    - name: 'Collect list of files by machines'
      set_fact:
        backup_files_by_machines: {}

    - name: 'Collect list of files by machines'
      set_fact:
        backup_files_by_machines: >-
          {{
            backup_files_by_machines | combine({
              hostvars[instance].ansible_host:
                backup_files_by_machines[hostvars[instance].ansible_host] | default([])
                  + hostvars[instance].instance_backup_files
            })
          }}
      with_items: '{{ play_hosts }}'
      loop_control:
        loop_var: instance
      run_once: true

    - name: 'Create archives with backups by machines'
      archive:
        dest: /opt/backups/{{ cartridge_app_name }}.{{ ansible_host }}.tar.gz
        path: '{{ backup_files_by_machines[ansible_host] }}'
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
[root@vm1 /]# tar -ztf /opt/backups/myapp.vm1.tar.gz
memtx/myapp.instance-1/00000000000000000004.snap
data/myapp.instance-1/config/auth.yml
data/myapp.instance-1/config/vshard_groups.yml
data/myapp.instance-1/config/topology.yml
conf.d/myapp.instance-1.yml
conf.d/myapp.yml
memtx/myapp-stateboard/00000000000000000049.snap
conf.d/myapp-stateboard.yml

[root@vm2 /]# tar -ztf /opt/backups/myapp.vm2.tar.gz
memtx/myapp.instance-2/00000000000000000004.snap
data/myapp.instance-2/config/auth.yml
data/myapp.instance-2/config/vshard_groups.yml
data/myapp.instance-2/config/topology.yml
conf.d/myapp.instance-2.yml
conf.d/myapp.yml
```
