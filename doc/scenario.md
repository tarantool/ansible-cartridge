# Role Scenario

The role uses a scenario to determine what to do.
Any scenario consists of the previously defined steps.
Using a scenario, you can:

- run the specified steps in any order, but API must be followed
  (with `cartridge_scenario` or `tasks_from`);
- replace the steps of the role with your own or add new steps
  (with `cartridge_custom_steps_dir` or `cartridge_custom_steps`).

## Steps

It's possible to specify what steps should be launched by `cartridge_scenario` variable or `tasks_from` option.

### Variable `cartridge_scenario`

To specify `cartridge_scenario`, you can use the following options:

- specify `cartridge_scenario` directly;
- specify a name of defined (by the role or by you) scenario by `cartridge_scenario_name`.

If you want to specify `cartridge_scenario` variable, you should specify names of steps.
The default scenario includes the following steps:

- [deliver_package](#deliver_package)
- [update_package](#update_package)
- [update_instance](#update_instance)
- [configure_instance](#configure_instance)
- [restart_instance](#restart_instance)
- [wait_instance_started](#wait_instance_started)
- [connect_to_membership](#connect_to_membership)
- [edit_topology](#edit_topology)
- [cleanup_expelled](#cleanup_expelled)
- [configure_auth](#configure_auth)
- [upload_app_config](#upload_app_config)
- [configure_app_config](#configure_app_config)
- [bootstrap_vshard](#bootstrap_vshard)
- [configure_failover](#configure_failover)
- [wait_members_alive](#wait_members_alive)
- [wait_cluster_has_no_issues](#wait_cluster_has_no_issues)
- [cleanup](#cleanup)

More scenarios you can see in [scenarios](#scenarios) section.

There are additional steps that are not included in the default scenario, but can be used in a custom one:

- [set_control_instance](#set_control_instance)
- [rotate_dists](#rotate_dists)
- [failover_promote](#failover_promote)
- [force_leaders](#force_leaders)
- [eval](#eval)
- [eval_on_control_instance](#eval_on_control_instance)
- [stop_instance](#stop_instance)
- [start_instance](#start_instance)
- [restart_instance_force](#restart_instance_force)
- [patch_instance_in_runtime](#patch_instance_in_runtime)

To replace the steps of the role with your own or add new steps, you should use `cartridge_custom_steps_dir`
or `cartridge_custom_steps` options (see [examples](#examples)).

### Option `tasks_from`

You can also select a step when importing a role.
To do this, you just need to specify in the `tasks_from` option
the name of the role step with the prefix `step_`.
Unfortunately, using this method you cannot import custom steps
(defined by `cartridge_custom_steps_dir` or `cartridge_custom_steps` options).

For example:

```yaml
- name: Step imported by 'tasks_from'
  hosts: all
  tasks:
    - name: Import step 'deliver_package'
      import_role:
        name: ansible.cartridge
        tasks_from: step_deliver_package
```

## Scenarios

In addition to the default scenario (see [steps](#steps)), there are also the following scenarios:
- `configure_instances`:
  - [deliver_package](#deliver_package)
  - [update_package](#update_package)
  - [update_instance](#update_instance)
  - [configure_instance](#configure_instance)
  - [restart_instance](#restart_instance)
  - [wait_instance_started](#wait_instance_started)
  - [wait_cluster_has_no_issues](#wait_cluster_has_no_issues)
  - [cleanup](#cleanup)
- `configure_topology`:
  - [connect_to_membership](#connect_to_membership)
  - [edit_topology](#edit_topology)
  - [cleanup_expelled](#cleanup_expelled)
  - [wait_members_alive](#wait_members_alive)
  - [wait_cluster_has_no_issues](#wait_cluster_has_no_issues)
  - [cleanup](#cleanup)
- `configure_app`:
  - [configure_auth](#configure_auth)
  - [configure_app_config](#configure_app_config)
  - [bootstrap_vshard](#bootstrap_vshard)
  - [configure_failover](#configure_failover)
  - [wait_members_alive](#wait_members_alive)
  - [wait_cluster_has_no_issues](#wait_cluster_has_no_issues)
  - [cleanup](#cleanup)

To add new scenarios or replace the role scenarios with your own, you should use `cartridge_custom_scenarios` option
(see [example](#add-a-custom-scenario-to-gradually-update-to-a-new-version-of-TGZ)).

## Examples

### Adding custom step to scenario

You can create your own step and include it to scenario. Let's create `./custom_steps/special_magic.yml`. After that,
you can add `special_magic` step to scenario. Just pass path to a directory where your custom steps are placed:

```yaml
- name: Deploy application
  hosts: all
  vars:
    cartridge_custom_steps_dir: "./custom_steps"
    cartridge_scenario:
      - restart_instance
      - special_magic
  roles:
    - tarantool.cartridge
```

### Importing steps from different directories

If you want to import steps by full paths, `cartridge_custom_steps` parameter can be useful. It allows specifying
mapping between step name and path to file to import:

```yaml
cartridge_custom_steps:
  - name: 'common_special_task'
    file: './common/special_task.yml'
```

### Override task from default scenario

Sometimes we need to use default scenario, but change some steps realizations.

For example, in default scenario package specified by `cartridge_package_path` is simple copied to remote host by
step `deliver_package`. We might want to deliver package to remote machine by our own way. Let's do it!

Generally, we just need to override default `deliver_package` step.

Let's take a look on it's [API](#deliver_package). It requires two variables:

- `cartridge_package_path` that we simply specify in vars;
- `single_instances_for_each_machine` that allows us to run this task once per each machine.

As a result of this module we should set `delivered_package_path` variable
(a path of package on a remote machine).

Now, choose a directory where our custom steps are placed, for example `./custom_steps`.

Then create `./custom_steps/deliver_package.yml` and describe a way to deliver package:

```yaml
# ./custom_steps/deliver_package.yml

- when:
    - cartridge_package_path is not none
    - inventory_hostname in single_instances_for_each_machine
  tags: cartridge-instances
  block:
    - name: 'Download package'
      get_url:
        url: 'https://some-server/myapp-1.0.0-0.rpm'
        dest: '/tmp'
      register: downloaded_package

    - name: 'Set delivered package path'
      set_fact:
        delivered_package_path: '{{ downloaded_package.dest }}'
```

Import role and say where to find our custom steps:

```yaml
# deploy_application.yml

- name: Deploy application
  hosts: all
  vars:
    cartridge_custom_steps_dir: "./custom_steps"
  roles:
    - tarantool.cartridge
```

### Editing topology without connecting to membership

Now there is a big problem on deploying huge clusters - [`connect_to_membership` step](#connect_to_membership) is too
long. Using scenario, we can solve this problem until it isn't solved in `cartridge`.

In fact `connect_to_membership` is used in [`set_control_instance` step](#set_control_instance) to find some instance
that is already in a cluster. This instance should be used for joining other instances (otherwise two different clusters
are created). This instance is called `control_instance` and is used for editing topology and configuring cluster (auth,
config and so on). Generally, `connect_to_membership` step can be skipped if you definitely know some instance that is
already joined to cluster. The solution is to set `cartridge_control_instance` fact manually and
remove `connect_to_membership` step from scenario:

```yaml
# edit_topology_playbook.yml

- name: Edit topology by core 1
  hosts: all
  vars:
    cartridge_scenario:
      - edit_topology
    cartridge_control_instance:
      name: core_1
      console_sock: '/var/run/tarantool/core_1.control'
  roles:
    - tarantool.cartridge
```

### Add a custom scenario to gradually update to a new version of TGZ

If you are using multiversion, then most likely you are upgrading to the new version of the package gradually:
first storages, then routers, etc. To do this, the same scenario to update the package version is used several times.
Let's remove duplication by declaring a custom scenario and then using it!

Firstly you should to define custom scenarios in hosts file:

```yaml
cartridge_multiversion: true
cartridge_package_path: "./myapp-2.0.0-0.tgz"
cartridge_custom_scenarios:
  # To deploy TGZ without instances update
  deploy_tgz:
    - deliver_package
    - update_package
  # To update instances to new TGZ
  update_instance_tgz:
    - update_instance
    - restart_instance
    - wait_instance_started
```

Then you can use them in your playbook:

```yaml
- name: Deploy new TGZ
  hosts: all
  vars:
    cartridge_scenario_name: "deploy_tgz"
  roles: tarantool.cartridge

- name: Update storages
  hosts: "*storage*"
  vars:
    cartridge_scenario_name: "update_instance_tgz"
  roles: tarantool.cartridge

- name: Update routers
  hosts: "*router*"
  vars:
    cartridge_scenario_name: "update_instance_tgz"
  roles: tarantool.cartridge
```

### Replace a role scenario with a custom scenario

To replace any role scenario with a custom one, you only should define your own scenario
in `cartridge_custom_scenarios` with the same name as the role script.

For example, you can replace `configure_topology` with a scenario without `connect_to_membership` step (see
[example for editing topology without connecting to membership](#editing-topology-without-connecting-to-membership))
```yaml
cartridge_custom_scenarios:
  configure_topology:
    - edit_topology
    - cleanup_expelled
```

## Role Facts Descriptions

Some of useful facts are established during preparation, so you can use them at any step:

- `instance_info` - information for a current instance. It's a dictionary with fields:
  - `app_conf_file` - path to file with application config;
  - `conf_file` - path to file with instance config;
  - `instance_id` - ID of instance (e.g. for section name in config file);
  - `console_sock` - path to control socket of instance;
  - `pid_file` - path to pid file of instance;
  - `work_dir` - path to working directory of instance;
  - `tmpfiles_conf` - path to config file of temporary files;
  - `dist_dir` - path to directory of distributed package;
  - `instance_dist_dir` - path to instance link to distributed package;
- `single_instances_for_each_machine` - list of instances (Ansible hosts), one for each physical machine. Can be used,
  for example, in `delegate_to`;
- `scenario_steps` - description of scenario steps. Each step is a dictionary with fields:
  - `name` - name of step;
  - `path` - path to YAML file of step.

## Role Steps Description

### deliver_package

Delivery of the application package to physical machines.

Input facts (set by role):

- `single_instances_for_each_machine` - list of instances (Ansible hosts), one for each physical machine.

Input facts (set by config):

- `cartridge_package_path` - path to file of package to delivery.

Output facts:

- `delivered_package_path` - remote path to file of delivered package.

### update_package

Install the delivered package on physical machines.

Input facts (set by role):

- `delivered_package_path` - remote path to file of delivered package.
  Is set on role preparation if `cartridge_delivered_package_path` is specified;
- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions));
- `single_instances_for_each_machine` - list of instances (Ansible hosts), one for each physical machine;
- `needs_restart` - if instance should be restarted to apply code or configuration changes
  (to determine if it's should be checked if instance should be restarted).

Input facts (set by config):

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

Output facts:

- `package_info` - information about delivered package. It's a dictionary with fields:
  - `name` - application name;
  - `tnt_version` - version of Tarantool required by application;
  - `type` - type of package (`rpm`, `deb` or `tgz`).
- `systemd_units_info` - information for systemd Units files. It's a dictionary with fields:
  - `stateboard_name` - ID of stateboard instance;
  - `app_unit_file` - filename of application Unit file;
  - `stateboard_unit_file` - filename of stateboard Unit file;
  - `instance_work_dir` - path to working directory of instance;
  - `stateboard_work_dir` - path to working directory of stateboard;
  - `instance_memtx_dir` - path to memtx directory of instance;
  - `stateboard_memtx_dir` - path to memtx directory of stateboard;
  - `instance_vinyl_dir` - path to vinyl directory of instance;
  - `stateboard_vinyl_dir` - path to vinyl directory of stateboard;
  - `instance_wal_dir` - path to wal directory of instance;
  - `stateboard_wal_dir` - path to wal directory of stateboard;
  - `instance_pid_file` - path to pid file of instance;
  - `stateboard_pid_file` - path to pid file of stateboard;
  - `instance_console_sock` - path to control socket of instance;
  - `stateboard_console_sock` - path to control socket of stateboard;
  - `instance_entrypoint` - path to Lua entrypoint file of instance;
  - `stateboard_entrypoint` - path to Lua entrypoint file of stateboard;
  - `instance_tarantool_binary` - path Tarantool binary file of instance;
  - `stateboard_tarantool_binary` - path Tarantool binary file of stateboard;
- `needs_restart` - if instance should be restarted to apply code or configuration changes.

### update_instance

Update instance links for a new version of package (if
[multiversion approach](/doc/multiversion.md) is enabled).

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions));
- `needs_restart` - if instance should be restarted to apply code or configuration changes
  (to determine if it's should be checked if instance should be restarted).

Input facts (set by config):

- `cartridge_package_path` - should be specified to compute app distribution directory
  (otherwise, `update_instance` is skipped);
- `expelled` - indicates if instance must be expelled from topology;
- `restarted` - if instance should be restarted or not (user forced decision);
- `cartridge_multiversion` - indicates that
  [multiversion approach](/doc/multiversion.md) is enabled;
- `cartridge_app_user` - user which will own the links;
- `cartridge_app_group` - group which will own the links.

Output facts:

- `needs_restart` - if instance should be restarted to apply code or configuration changes.

### configure_instance

Configure instance in runtime and change instance config.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions));
- `needs_restart` - if instance should be restarted to apply code or configuration changes
  (to determine if it's should be checked if instance should be restarted).

Input facts (set by config):

- `config` - instance configuration ([more details here](/doc/instances.md));
- `restarted` - if instance should be restarted or not (user forced decision);
- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `cartridge_app_name` - application name;
- `cartridge_cluster_cookie` - cluster cookie for all cluster instances;
- `cartridge_not_save_cookie_in_app_config` - flag indicates that cluster cookie shouldn't be persisted in application configuration file;
- `cartridge_defaults` - default configuration parameters values for instances;
- `cartridge_app_user` - user which will own the links;
- `cartridge_app_group` - group which will own the links.

Output facts:

- `needs_restart` - if instance should be restarted to apply code or configuration changes.

### restart_instance

Restart and enable instance systemd service if it should be restarted.

Input facts (set by role):

- `needs_restart` - if instance should be restarted to apply code or configuration changes;
- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `cartridge_cluster_cookie` - cluster cookie for all cluster instances (is needed to check if configuration file was changed);
- `cartridge_not_save_cookie_in_app_config` - flag indicates that cluster cookie shouldn't be persisted in application configuration file;
- `restarted` - if instance should be restarted or not (user forced decision).

### wait_instance_started

Wait until an instance is fully started.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `instance_start_timeout` - time in seconds to wait for instance to be started;
- `cartridge_wait_buckets_discovery` - indicates if routers should wait for buckets discovery after vshard bootstrap.

### connect_to_membership

Connect an instance to membership.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `cartridge_app_name` - application name;
- `config` - instance configuration ([more details here](/doc/instances.md)).

Output facts:

- `alive_not_expelled_instance` - information about one not expelled instance
  ([more details here](#role-facts-descriptions)).

### set_control_instance

Find some instance that can be used for editing topology and configuring cluster.
This is instance that is:

* described in inventory;
* have `alive` status in membership;
* if there are some instances already joined to cluster, then one of them is used,
  otherwise, any instance that should be joined during current play is chosen;
* control instance should have minimal Cartridge version across all suitable
  instances (because Cartridge two-phase commit should be called by instance
  that has lowest version).

Steps that require control instance (such as [`edit_topology`](#edit_topology))
call `set_control_instance` implicitly if `control_instance` fact isn't set.

`control_instance` fact can be set by user via `cartridge_control_instance` variable.
In this case `control_instance` fact is initialized on preparation step.

**This step should be launched only after `connect_to_membership` step. Otherwise, 2 clusters may be created!**

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `replicaset_alias` - replicaset alias, will be displayed in Web UI;

Output facts:

- `control_instance` - information about control instance, that should be used for
  managing topology and configuring cluster. It's a dictionary with fields:
  - `name` - instance name (Ansible host);
  - `console_sock` - path to control socket of instance.

- `alive_not_expelled_instance` - information about one not expelled instance. It's a dictionary with fields:
  - `name` - instance name (Ansible host);
  - `console_sock` - path to control socket of instance.

### edit_topology

Edit topology of replicasets.

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance)).

Input facts (set by config):

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

### cleanup_expelled

Cleanup files if instance is expelled.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `expelled` - indicates if instance must be expelled from topology;

### configure_auth

Configure application authentication settings.

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance)).

Input facts (set by config):

- `cartridge_auth` - authorization configuration.

### upload_app_config

Upload application configuration (mode details in [application config doc](/doc/app_config.md#config-uploading)).

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance)).

Input facts (set by config):

- `cartridge_app_config_path` - path to application config to patch;
- `cartridge_app_config_upload_mode` - mode of config uploading (`lua`, `http` or `tdg`);
- `cartridge_app_config_upload_url` - url of instance to upload config
  (`http://127.0.0.1:{control_instance.http_port}/admin/config` by default);
- `cartridge_cluster_cookie` - cluster cookie for all cluster instances;
- `cartridge_tdg_token` - token to upload config by HTTP in TDG.

### configure_app_config

Configure application configuration.

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance)).

Input facts (set by config):

- `cartridge_app_config` - application config sections to patch.

### bootstrap_vshard

Bootstrap VShard in cluster.

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance));
- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `cartridge_bootstrap_vshard` - indicates if vshard should be bootstrapped;
- `instance_discover_buckets_timeout` - time in seconds to wait for instance to discover buckets;
- `cartridge_wait_buckets_discovery` - indicates if routers should wait for buckets discovery after vshard bootstrap;

### configure_failover

Configure application failover.

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance)).

Input facts (set by config):

- [DEPRECATED] `cartridge_failover` - indicates if eventual failover should be enabled or disabled;
- `cartridge_failover_params` - failover parameters.

### wait_members_alive

Waits until all cluster instances become alive and come to a specified state
(by default, it's `RolesConfigured`).

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance)).

Input facts (set by config):

- `allowed_members_states` - list of allowed states. If empty then instance state isn't checked;
- `wait_members_alive_retries` - retries to check that all instances become alive;
- `wait_members_alive_delay` - delay to retry instances status check.

### wait_cluster_has_no_issues

Waits until the cluster has no issues.

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance)).

Input facts (set by config):

- `wait_cluster_has_no_issues_retries` - retries to check that cluster has no issues;
- `wait_cluster_has_no_issues_delay` - delay to retry cluster issues check;
- `allow_warning_issues` - allow issues with `warning` level;
- `show_issues` - log cluster issues as a warnings;

### cleanup

Removes temporary files specified in `temporary_files` list.
By default, `temporary_files` is an empty list. The role,
depending on the scenario, can add the following files to this list:

- path to delivered package (`delivered_package_path` variable value);
- path to repository setup script.

In addition, you can add any files to this list by specifying `temporary_files` in configuration or in any custom step.
For example, you can make a step like this:

```yaml
- name: 'Add my temporary file'
  set_fact:
    temporary_files: "{{ temporary_files + ['/tmp/my_file'] }}"
```

Input facts (set by role):

- `temporary_files` - list of temporary files to remove.

Input facts (set by config):

- `cartridge_remove_temporary_files` - indicates if temporary files should be removed.

### rotate_dists

Rotate application distributions.

When [multiversion approach](/doc/multiversion.md) is used, each new application
version is added to `cartridge_app_install_dir`.
This step removes redundant distributions.

Input facts (set by config):

- `cartridge_app_name` - application name;
- `cartridge_app_install_dir` - path to directory where application distributions
  are placed;
- `cartridge_keep_num_latest_dists` - number of dists that should be kept.

Output facts:

- `dists_dirs_to_remove` - list of distribution directories paths that
  were removed.

### failover_promote

[Promotes leaders](/doc/rolling_update.md#using-failover_promote-step) according to specified
[`cartridge_failover_promote_params`](/doc/rolling_update.md#leaders-promotion).

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance));

Input facts (set by config):

- `cartridge_failover_promote_params` - promote leaders params. More details in
  [rolling update doc](/doc/rolling_update.md#leaders-promotion).

### force_leaders

[Promotes leaders](/doc/rolling_update.md#using-force_leaders-step)
to current play hosts (instances specified in limit).
More details in [rolling update doc](/doc/rolling_update.md).

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance));

Input facts (set by config):

- `cartridge_failover_promote_params` - promote leaders params.
  In fact, only `force_inconsistency` parameter is used (leaders are got from specified play hosts).
  More details in [rolling update doc](/doc/rolling_update.md).

### eval

[Eval code](/doc/eval.md) on instance.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `cartridge_eval_file` - path to file with Lua code to eval (isn't used if
  `cartridge_eval_body` is specified);
- `cartridge_eval_body` - code to eval;
- `cartridge_eval_args` - function arguments;
- `cartridge_eval_with_retries` - flag indicates that eval should be performed with retries;
- `cartridge_eval_retries` number of eval retries;
- `cartridge_eval_delay` - eval retries delay.

### eval_on_control_instance

[Eval code](/doc/eval.md) on control instance.

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance));
- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `cartridge_eval_file` - path to file with Lua code to eval (isn't used if
  `cartridge_eval_body` is specified);
- `cartridge_eval_body` - code to eval;
- `cartridge_eval_args` - function arguments;
- `cartridge_eval_with_retries` - flag indicates that eval should be performed with retries;
- `cartridge_eval_retries` number of eval retries;
- `cartridge_eval_delay` - eval retries delay.

### stop_instance

Stop and disable instance systemd service.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

### start_instance

Start and enable instance systemd service.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

### restart_instance_force

Restart and enable instance systemd service without any conditions.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

### patch_instance_in_runtime

Patch dynamic (see [parameters](https://www.tarantool.io/en/doc/latest/reference/configuration/#configuration-parameters)
with `Dynamic: yes`) instance parameters in runtime only
(now it's possible to change only `box` config parameters).
If the none-dynamic parameter is specified,
nothing will be changed, and an error will be returned.

**Note** that memory size can be only increased in runtime.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `cartridge_runtime_params` - new instance parameters ([more details here](/doc/instances.md));
- `expelled` - indicates if instance must be expelled from topology.
