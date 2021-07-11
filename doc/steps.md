# Role Steps

Here are described steps that can be combined in the role scenarios.
Each step description says what variables are required for the step and
what variables are set by step.

## Role Steps List

List of steps from default scenario:

- [deliver_package](#step-deliver_package)
- [update_package](#step-update_package)
- [update_instance](#step-update_instance)
- [configure_instance](#step-configure_instance)
- [restart_instance](#step-restart_instance)
- [wait_instance_started](#step-wait_instance_started)
- [connect_to_membership](#step-connect_to_membership)
- [edit_topology](#step-edit_topology)
- [cleanup_expelled](#step-cleanup_expelled)
- [configure_auth](#step-configure_auth)
- [upload_app_config](#step-upload_app_config)
- [configure_app_config](#step-configure_app_config)
- [bootstrap_vshard](#step-bootstrap_vshard)
- [configure_failover](#step-configure_failover)
- [wait_members_alive](#step-wait_members_alive)
- [wait_cluster_has_no_issues](#step-wait_cluster_has_no_issues)
- [cleanup](#step-cleanup)

Additional steps that are not included in the default scenario,
but can be used in a custom one:

- [set_control_instance](#step-set_control_instance)
- [rotate_dists](#step-rotate_dists)
- [failover_promote](#step-failover_promote)
- [force_leaders](#step-force_leaders)
- [eval](#step-eval)
- [eval_on_control_instance](#step-eval_on_control_instance)
- [stop_instance](#step-stop_instance)
- [start_instance](#step-start_instance)
- [restart_instance_force](#step-restart_instance_force)
- [patch_instance_in_runtime](#step-patch_instance_in_runtime)
- [cleanup_instance_files](#step-cleanup_instance_files)
- [backup](#step-backup)
- [backup_start](#step-backup_start)
- [backup_stop](#step-backup_stop)

## Role Variables Descriptions

Some of useful variables always establishes during role preparation, so them can be used by any step:

- `instance_info` - information for a current instance. It's a dictionary with fields:
  - `app_conf_file` - path to file with application config;
  - `conf_file` - path to file with instance config;
  - `instance_id` - ID of instance (e.g. for section name in config file);
  - `console_sock` - path to control socket of instance;
  - `pid_file` - path to pid file of instance;
  - `work_dir` - path to working directory of instance;
  - `memtx_dir` - path to memtx directory of instance;
  - `vinyl_dir` - path to vinyl directory of instance;
  - `wal_dir` - path to wal directory of instance;
  - `systemd_service` - name to systemd service;
  - `systemd_service_dir` - path to directory of systemd service extensions;
  - `systemd_service_env_file` - path to file of systemd service environment extensions;
  - `tmpfiles_conf` - path to config file of temporary files;
  - `dist_dir` - path to directory of distributed package;
  - `instance_dist_dir` - path to instance link to distributed package;
  - `paths_to_remove_on_expel` - paths that will be removed on instance expel;
  - `files_to_remove_on_cleanup` - files that will be removed on instance cleanup;
  - `dirs_to_remove_on_cleanup` - dirs that will be removed on instance cleanup;
- `single_instances_for_each_machine` - list of instances (Ansible hosts), one for each physical machine,
  for example, can be used in `delegate_to`;
- `instances_from_same_machine` - dictionary, where key is the hostname of the instance,
  value is the hostnames of instances from the same physical machine;
  so, you can use `instances_from_same_machine[inventory_hostname]` to get
  a list of instances placed on the same machine as the current one;
- `scenario_steps` - description of scenario steps. Each step is a dictionary with fields:
  - `name` - name of step;
  - `path` - path to YAML file of step.

## Step `deliver_package`

Delivery of the application package to physical machines.

Input variables from config:

- `cartridge_package_path` - path to file of package to delivery.

Output variables:

- `delivered_package_path` - remote path to file of delivered package.

## Step `update_package`

Install the delivered package on physical machines.

variables from steps completed before:

- `delivered_package_path` - remote path to file of delivered package.
  It's set in [deliver_package](#step-deliver_package) step. Also, it's set on role
  preparation if `cartridge_delivered_package_path` is specified.

Input variables from config:

- `expelled` - indicates if instance must be expelled from topology
  (to determine if it's should be checked if instance should be restarted);
- `restarted` - if instance should be restarted or not (user forced decision)
  (to determine if it's should be checked if instance should be restarted);
- `cartridge_app_name` - application name;
- `cartridge_enable_tarantool_repo` - indicates if Tarantool repository should be enabled;
- `cartridge_install_tarantool_for_tgz` - indicates if Tarantool should be enabled when use TGZ package;
- `cartridge_create_user_group_for_tgz` - flag indicates
  that specified user and group should be created;
- `cartridge_multiversion` - indicates that multiple package versions is enabled;
- `cartridge_configure_tmpfiles` - indicates that tmpfiles config should be configured;
- `cartridge_configure_systemd_unit_files` - indicates that systemd Unit files should be configured;
- `cartridge_app_user` - user which will own the links;
- `cartridge_app_group` - group which will own the links;
- `cartridge_run_dir` - path to directory of instances sockets;
- `cartridge_data_dir` - path to directory of instance data;
- `cartridge_memtx_dir` - path to memtx directory of instance;
- `cartridge_vinyl_dir` - path to vinyl directory of instance;
- `cartridge_wal_dir` - path to wal directory of instance;
- `cartridge_conf_dir` - path to directory of instances application configs;
- `cartridge_app_install_dir` - path to directory with application distributions;
- `cartridge_app_instances_dir` - path to directory with instances links to
  distributions (see [multiversion approach doc](/doc/multiversion.md)).

Output variables:

- `needs_restart` - if instance should be restarted to apply code or configuration changes.

## Step `update_instance`

Update instance links for a new version of package (if
[multiversion approach](/doc/multiversion.md) is enabled).

Input variables from config:

- `cartridge_package_path` - should be specified to compute app distribution directory
  (otherwise, `update_instance` is skipped);
- `expelled` - indicates if instance must be expelled from topology;
- `restarted` - if instance should be restarted or not (user forced decision);
- `cartridge_multiversion` - indicates that
  [multiversion approach](/doc/multiversion.md) is enabled;
- `cartridge_app_user` - user which will own the links;
- `cartridge_app_group` - group which will own the links.

Output variables:

- `needs_restart` - if instance should be restarted to apply code or configuration changes.

## Step `configure_instance`

Configure instance in runtime and change instance config.

Input variables from config:

- `config` - instance configuration ([more details here](/doc/instances.md));
- `restarted` - if instance should be restarted or not (user forced decision);
- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `cartridge_app_name` - application name;
- `cartridge_cluster_cookie` - cluster cookie for all cluster instances;
- `cartridge_not_save_cookie_in_app_config` - flag indicates that cluster cookie shouldn't be persisted in application configuration file;
- `cartridge_defaults` - default configuration parameters values for instances;
- `cartridge_app_user` - user which will own the links;
- `cartridge_app_group` - group which will own the links;
- `cartridge_systemd_dir` - directory where systemd-unit files should be placed;
- `cartridge_extra_env` - environment variables for instance service.

Output variables:

- `needs_restart` - if instance should be restarted to apply code or configuration changes.

## Step `restart_instance`

Restart and enable instance systemd service if it should be restarted.

variables from steps completed before:

- `needs_restart` - if instance should be restarted to apply code or
  configuration changes. It's set in [update_package](#step-update_package),
  [update_instance](#step-update_instance) and [configure_instance](#step-configure_instance)
  steps.

Input variables from config:

- `cartridge_cluster_cookie` - cluster cookie for all cluster instances (is needed to check if configuration file was changed);
- `cartridge_not_save_cookie_in_app_config` - flag indicates that cluster cookie shouldn't be persisted in application configuration file;
- `restarted` - if instance should be restarted or not (user forced decision).

## Step `wait_instance_started`

Wait until an instance is fully started.

Input variables from config:

- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `instance_start_retries` - retries to check that all instances become started;
- `instance_start_delay` - delay before retry to check that all instances become started;
- [DEPRECATED] `instance_start_timeout` - time in seconds to wait for instance to be started;
- `cartridge_wait_buckets_discovery` - indicates if routers should wait for buckets discovery after vshard bootstrap.

## Step `connect_to_membership`

Connect an instance to membership.

Input variables from config:

- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `cartridge_app_name` - application name;
- `config` - instance configuration ([more details here](/doc/instances.md));
- `connect_to_membership_retries` - retries to connect to membership;
- `connect_to_membership_delay` - delay before retry to connect to membership.

## Step `set_control_instance`

Find some instance that can be used for editing topology and configuring cluster.
This is instance that is:

* described in inventory;
* have `alive` status in membership;
* if there are some instances already joined to cluster, then one of them is used,
  otherwise, any instance that should be joined during current play is chosen;
* control instance should have minimal Cartridge version across all suitable
  instances (because Cartridge two-phase commit should be called by instance
  that has lowest version).

Steps that require control instance (such as [`edit_topology`](#step-edit_topology))
call `set_control_instance` implicitly if `control_instance` variable isn't set.

`control_instance` variable can be set by user via `cartridge_control_instance` variable.
In this case `control_instance` variable is initialized on preparation step.

**This step should be launched only after `connect_to_membership` step. Otherwise, 2 clusters may be created!**

Input variables from config:

- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `replicaset_alias` - replicaset alias, will be displayed in Web UI;

Output variables:

- `control_instance` - information about control instance, that should be used for
  managing topology and configuring cluster. It's a dictionary with fields:
  - `name` - instance name (Ansible host);
  - `console_sock` - path to control socket of instance.

## Step `edit_topology`

Edit topology of replicasets.

*If `control_instance` is not defined then [set_control_instance](#step-set_control_instance) will run.*

Input variables from config:

- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `replicaset_alias` - replicaset alias, will be displayed in Web UI;
- `roles` - roles to be enabled on the replicaset;
- `failover_priority` - failover priority order;
- `all_rw` - indicates that that all servers in the replicaset should be read-write;
- `weight` - vshard replicaset weight;
- `vshard_group` - vshard group;
- `twophase_netbox_call_timeout` - time in seconds to wait netbox call
  while two-phase commit (Cartridge 2.5+ is required);
- `twophase_upload_config_timeout` - time in seconds to wait config upload
  while two-phase commit (Cartridge 2.5+ is required);
- `twophase_apply_config_timeout` - time in seconds to wait config apply
  while two-phase commit (Cartridge 2.5+ is required);
- `edit_topology_healthy_timeout` - time in seconds to wait until a cluster become healthy after editing topology;
- [DEPRECATED] `edit_topology_timeout` - the same timeout as `edit_topology_healthy_timeout`.

## Step `cleanup_expelled`

Cleanup files if instance is expelled.

Input variables from config:

- `expelled` - indicates if instance must be expelled from topology;

## Step `configure_auth`

Configure application authentication settings.

*If `control_instance` is not defined then [set_control_instance](#step-set_control_instance) will run.*

Input variables from config:

- `cartridge_auth` - authorization configuration.

## Step `upload_app_config`

Upload application configuration (mode details in [application config doc](/doc/app_config.md#config-uploading)).

*If `control_instance` is not defined then [set_control_instance](#step-set_control_instance) will run.*

Input variables from config:

- `cartridge_app_config_path` - path to application config to upload;
- `cartridge_app_config_upload_mode` - mode of config uploading (`lua`, `http` or `tdg`);
- `cartridge_app_config_upload_url` - url of instance to upload config
  (`http://127.0.0.1:{control_instance.http_port}/admin/config` by default);
- `cartridge_cluster_cookie` - cluster cookie for all cluster instances;
- `cartridge_tdg_token` - token to upload config by HTTP in TDG.

## Step `configure_app_config`

Configure application configuration.

*If `control_instance` is not defined then [set_control_instance](#step-set_control_instance) will run.*

Input variables from config:

- `cartridge_app_config` - application config sections to patch.

## Step `bootstrap_vshard`

Bootstrap VShard in cluster.

*If `control_instance` is not defined then [set_control_instance](#step-set_control_instance) will run.*

Input variables from config:

- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `cartridge_bootstrap_vshard` - indicates if vshard should be bootstrapped;
- `bootstrap_vshard_retries` - retries to bootstrap vshard;
- `bootstrap_vshard_delay` - delay before retry to bootstrap vshard;
- `instance_discover_buckets_retries` - retries to check that instances discover buckets;
- `instance_discover_buckets_delay` - delay before retry to check that instances discover buckets;
- [DEPRECATED] `instance_discover_buckets_timeout` - time in seconds to wait for instance to discover buckets;
- `cartridge_wait_buckets_discovery` - indicates if routers should wait for buckets discovery after vshard bootstrap;

## Step `configure_failover`

Configure application failover.

*If `control_instance` is not defined then [set_control_instance](#step-set_control_instance) will run.*

Input variables from config:

- `cartridge_failover_params` - failover parameters;
- [DEPRECATED] `cartridge_failover` - indicates if eventual failover should be enabled or disabled.

## Step `wait_members_alive`

Waits until all cluster instances become alive and come to a specified state
(by default, it's `RolesConfigured`).

*If `control_instance` is not defined then [set_control_instance](#step-set_control_instance) will run.*

Input variables from config:

- `allowed_members_states` - list of allowed states. If empty then instance state isn't checked;
- `wait_members_alive_retries` - retries to check that all instances become alive;
- `wait_members_alive_delay` - delay to retry instances status check.

## Step `wait_cluster_has_no_issues`

Waits until the cluster has no issues.

*If `control_instance` is not defined then [set_control_instance](#step-set_control_instance) will run.*

Input variables from config:

- `wait_cluster_has_no_issues_retries` - retries to check that cluster has no issues;
- `wait_cluster_has_no_issues_delay` - delay to retry cluster issues check;
- `allow_warning_issues` - allow issues with `warning` level;
- `show_issues` - log cluster issues as a warnings;

## Step `cleanup`

Removes temporary files specified in `temporary_files` list.
By default, `temporary_files` is an empty list. The role,
depending on the scenario, can add the following files to this list:

- path to delivered package (`delivered_package_path` variable value
  from [deliver_package](#step-deliver_package) step);
- path to repository setup script (from [update_package](#step-update_package) step).

In addition, you can add any files to this list by specifying `temporary_files` in configuration or in any custom step.
For example, you can make a step like this:

```yaml
- name: 'Add my temporary file'
  set_fact:
    temporary_files: "{{ temporary_files + ['/tmp/my_file'] }}"
```

Input variables (set by role):

- `temporary_files` - list of temporary files to remove.

Input variables from config:

- `cartridge_remove_temporary_files` - indicates if temporary files should be removed.

## Step `rotate_dists`

Rotate application distributions.

When [multiversion approach](/doc/multiversion.md) is used, each new application
version is added to `cartridge_app_install_dir`.
This step removes redundant distributions.

Input variables from config:

- `cartridge_app_name` - application name;
- `cartridge_app_install_dir` - path to directory where application distributions
  are placed;
- `cartridge_keep_num_latest_dists` - number of dists that should be kept.

Output variables:

- `dists_dirs_to_remove` - list of distribution directories paths that
  were removed.

## Step `failover_promote`

[Promotes leaders](/doc/rolling_update.md#using-failover_promote-step) according to specified
[`cartridge_failover_promote_params`](/doc/rolling_update.md#leaders-promotion).

*If `control_instance` is not defined then [set_control_instance](#step-set_control_instance) will run.*

Input variables from config:

- `cartridge_failover_promote_params` - promote leaders params. More details in
  [rolling update doc](/doc/rolling_update.md#leaders-promotion).

## Step `force_leaders`

[Promotes leaders](/doc/rolling_update.md#using-force_leaders-step)
to current play hosts (instances specified in limit).
More details in [rolling update doc](/doc/rolling_update.md).

*If `control_instance` is not defined then [set_control_instance](#step-set_control_instance) will run.*

Input variables from config:

- `cartridge_failover_promote_params` - promote leaders params.
  In variable, only `force_inconsistency` parameter is used (leaders are got from specified play hosts).
  More details in [rolling update doc](/doc/rolling_update.md).

## Step `eval`

[Eval code](/doc/eval.md) on instance.

Input variables from config:

- `cartridge_eval_file` - path to file with Lua code to eval (isn't used if
  `cartridge_eval_body` is specified);
- `cartridge_eval_body` - code to eval;
- `cartridge_eval_args` - function arguments;
- `cartridge_eval_with_retries` - flag indicates that eval should be performed with retries;
- `cartridge_eval_retries` number of eval retries;
- `cartridge_eval_delay` - eval retries delay.

## Step `eval_on_control_instance`

[Eval code](/doc/eval.md) on control instance.

*If `control_instance` is not defined then [set_control_instance](#step-set_control_instance) will run.*

Input variables from config:

- `cartridge_eval_file` - path to file with Lua code to eval (isn't used if
  `cartridge_eval_body` is specified);
- `cartridge_eval_body` - code to eval;
- `cartridge_eval_args` - function arguments;
- `cartridge_eval_with_retries` - flag indicates that eval should be performed with retries;
- `cartridge_eval_retries` number of eval retries;
- `cartridge_eval_delay` - eval retries delay.

## Step `stop_instance`

Stop and disable instance systemd service.

## Step `start_instance`

Start and enable instance systemd service.

## Step `restart_instance_force`

Restart and enable instance systemd service without any conditions.

## Step `patch_instance_in_runtime`

Patch dynamic (see [parameters](https://www.tarantool.io/en/doc/latest/reference/configuration/#configuration-parameters)
with `Dynamic: yes`) instance parameters in runtime only
(now it's possible to change only `box` config parameters).
If the none-dynamic parameter is specified,
nothing will be changed, and an error will be returned.

**Note** that memory size can be only increased in runtime.

Input variables from config:

- `cartridge_runtime_params` - new instance parameters ([more details here](/doc/instances.md));
- `expelled` - indicates if instance must be expelled from topology.

## Step `cleanup_instance_files`

Clean up data of stopped instance.
If instance is running, an error will be returned.

Input variables from config:

- `cartridge_paths_to_keep_on_cleanup` - list of full paths or relative paths
  to work/memtx/vinyl/wal directory that should be kept on instance cleanup
  (it's possible to use bash patterns, e.g. `*.control`).


### Step `backup`

Create a [backup](/doc/backup.md) archive for each instance and fetch it on the local machine.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions));
- `single_instances_for_each_machine` that allows us to run this task once per each machine.

Input facts (set by config):

- `cartridge_remote_backups_dir` - directory to store backups on the remote;
- `cartridge_fetch_backups` - flag indicates that backups should be fetched the local machine;
- `cartridge_fetch_backups_dir` -  a directory on the local machine where backups should be fetched if `cartridge_fetch_backups` is `true`. This path is relative to the playbook path;
- `cartridge_app_user` - user which will own the links;
- `cartridge_app_group` - group which will own the links;
- `stateboard` - indicates that the instance is a stateboard.

Output facts:

- `instance_backup_files` - list of instance files to back up;
- `backup_archive_path` - path to the instance backup archive on the remote machine;
- `fetched_backup_archive_path` - path to the fetched backup file (is set only if `cartridge_fetch_backups` is `true`).

### Step `backup_start`

Start a [backup](/doc/backup.md) process on the instance.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `stateboard` - indicates that the instance is a stateboard.

Output facts:

- `instance_backup_files` - list of instance files that should be added to backup archive.

### Step `backup_stop`

Stop started [backup](/doc/backup.md) on the instance.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).
