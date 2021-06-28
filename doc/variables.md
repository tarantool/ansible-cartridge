# Role variables

Role variables are used to configure started instances, cluster topology,
vshard bootstrapping, and failover.

## Common variables

* `cartridge_app_name` (`string`): application name, required;
* `cartridge_cluster_cookie` (`string`): cluster cookie for all
  cluster instances;
* `cartridge_not_save_cookie_in_app_config` (`boolean`, default: `false`) - flag indicates that cluster cookie shouldn't be persisted in application configuration file;
* `cartridge_remove_temporary_files` (`boolean`, optional, default: `false`):
  indicates if temporary files should be removed
  (more details in description of [`cleanup` step API](/doc/scenario.md#cleanup));
* `cartridge_paths_to_keep_on_cleanup` (`list-of-strings`, optional, default: `[]`) -
  list of full paths or relative paths to work/memtx/vinyl/wal
  directory that should be kept on instance cleanup
  (it's possible to use bash patterns, e.g. `*.control`).

## Role scenario configuration

For more details see [scenario documentation](/doc/scenario.md).

* `cartridge_scenario` (`list-of-strings`): list of steps to be launched
  (see [change scenario](/README.md#using-scenario) for more details);
* `cartridge_custom_steps_dir` (`string`, default: `null`): path to directory
  containing YAML files of custom steps (see [change scenario](/README.md#using-scenario) for more details);
* `cartridge_custom_steps` (`list-of-dicts`, default: `[]`): list of custom steps
  (see [change scenario](/README.md#using-scenario) for more details);
* `cartridge_scenario_name` (`string`, default: `default`): name of scenario to be launched;
* `cartridge_custom_scenarios` (`dict-of-lists`, default: `{}`): dictionary of custom scenarios;

## Application package configuration

* `cartridge_package_path` (`string`): path to application package;
* `cartridge_enable_tarantool_repo` (`boolean`, default: `true`):
  indicates if the Tarantool repository should be enabled (for packages with
  open-source Tarantool dependency);

## TGZ specific configuration

* `cartridge_multiversion` (`boolean`, default: `false`): use [multiversion
  approach](/doc/multiversion.md) for TGZ package.

* `cartridge_install_tarantool_for_tgz` (`boolean`, default: `false`): flag indicates
  that Tarantool should be installed if application distribution doesn't contain `tarantool`
  binary; Tarantool version is got from `VERSION` file that is placed in distribution
  by Cartridge CLI;

* `cartridge_create_user_group_for_tgz` (`boolean`, default: `false`): flag indicates
  that specified user and group should be created.

* `cartridge_app_user` (`string`, default: `tarantool`): application user;
* `cartridge_app_group` (`string`, default: `tarantool`): application group;

* `cartridge_data_dir` (`string`, default: `/var/lib/tarantool`): directory
  where instances working directories are placed;
* `cartridge_memtx_dir_parent` (`string`): directory where instances memtx directories are placed;
* `cartridge_vinyl_dir_parent` (`string`): directory where instances vinyl directories are placed;
* `cartridge_wal_dir_parent` (`string`): directory where instances WAL directories are placed;
* `cartridge_run_dir`(`string`, default: `/var/run/tarantool`): directory where
  PID and socket files are stored;
* `cartridge_conf_dir` (`string`, default: `/etc/tarantool/conf.d`): path to
  instances configuration;
* `cartridge_app_install_dir` (`string`, default: `/usr/share/tarantool`): directory
  where application distributions are placed;
* `cartridge_app_instances_dir` (`string`, default: `/usr/share/tarantool`): directory
  where instances distributions are placed in case of multiversion approach.

* `cartridge_configure_systemd_unit_files` (`boolean`, default: `true`): flag indicates that
  systemd unit files should be configured;
* `cartridge_systemd_dir` (`string`, default: `/etc/systemd/system`): directory where
  systemd-unit files should be placed;

* `cartridge_configure_tmpfiles` (`boolean`, default: `true`): flag indicates that tmpfiles
  config should be configured for application run dir;
* `cartridge_tmpfiles_dir` (`string`, default: `/usr/lib/tmpfiles.d/`): a directory where
  tmpfile configuration should be placed;

* `cartridge_keep_num_latest_dists` (`number`, default: 2): the number of application
  versions that should be kept during distribution rotation;

## Instances configuration

* `cartridge_defaults` (`dict`, default: `{}`): default configuration
  parameters values for instances;
* `config` (`dict`, required): [instance configuration](/doc/instances.md);
* `zone` (`string`): instance zone (available since
  [Cartridge 2.4.0](https://github.com/tarantool/cartridge/releases/tag/2.4.0));
* `cartridge_extra_env` (`dict`): environment variables for instance service;
* `cartridge_runtime_params` (`dict`): [instance configuration](/doc/instances.md)
  parameters to patch in runtime;
* `restarted` (`boolean`): flag indicates if instance should be
  restarted or not (if this flag isn't specified, instance will be restarted if
  it's needed to apply configuration changes);
* `expelled` (`boolean`, default: `false`): a boolean flag that indicates if instance must be expelled from topology;
* `stateboard` (`boolean`, default: `false`): a boolean flag that indicates
   that the instance is a [stateboard](/doc/stateboard.md);
* `instance_start_retries` (`number`, default: 10) retries to check that all instances become started;
* `instance_start_delay` (`number`, default: 5): delay before retry to check that all instances become started;
* [DEPRECATED] `instance_start_timeout` (`number`, default: 60): time in seconds to wait for instance to be started;
* `cartridge_wait_buckets_discovery` (`boolean`, default: `true`): a boolean
  flag that indicates if routers should wait for buckets discovery after vshard bootstrap;
* `instance_discover_buckets_retries` (`number`, default: 20) retries to check that instances discover buckets;
* `instance_discover_buckets_delay` (`number`, default: 5): delay before retry to check that instances discover buckets;
* [DEPRECATED] `instance_discover_buckets_timeout` (`number`, default: 60): time in seconds
  to wait for instance to discover buckets;
* `allowed_members_states` (`list-of-strings`, default: `[RolesConfigured]`):
  list of allowed instance states;
* `wait_members_alive_retries` (`number`, default: 10) retries to check that all instances become alive;
* `wait_members_alive_delay` (`number`, default: 5): delay before retry to check that all instances become alive;

## Replicasets configuration

* `replicaset_alias` (`string`): replicaset alias, will be displayed in Web UI;
* `failover_priority` (`list-of-strings`): failover priority;
* `roles` (`list-of-strings`, required if `replicaset_alias` specified): roles to be enabled on the replicaset;
* `all_rw` (`boolean`): indicates that that all servers in the replicaset should be read-write;
* `vshard_group` (`string`): name of vshard group the replicaset belongs to;
* `weight` (`number`): vshard replicaset weight (matters only if `vshard-storage` role is enabled);
* `twophase_netbox_call_timeout` (`number`): time in seconds to wait netbox call
  while two-phase commit (Cartridge 2.5+ is required);
* `twophase_upload_config_timeout` (`number`): time in seconds to wait config upload
  while two-phase commit (Cartridge 2.5+ is required);
* `twophase_apply_config_timeout` (`number`): time in seconds to wait config apply
  while two-phase commit (Cartridge 2.5+ is required);
* `edit_topology_healthy_timeout` (`number`, default: `60`): time in seconds to wait until a cluster become
  healthy after editing topology;
* [DEPRECATED] `edit_topology_timeout` - the same timeout as `edit_topology_healthy_timeout`.
* `edit_topology_allow_missed_instances` (`boolean`, default: `false`) - if set, then
  instances that aren't started yet are ignored on editing topology. A warning
  message is shown in case of error.

## Cluster configuration

* `connect_to_membership_retries` (`number`, default: 3): retries to connect to membership;
* `connect_to_membership_delay` (`number`, default: 5): delay before retry to connect to membership;
* `cartridge_bootstrap_vshard` (`boolean`, default: `false`): a boolean
  flag that indicates if vshard should be bootstrapped;
* `bootstrap_vshard_retries` (`number`, default: 3): retries to bootstrap vshard;
* `bootstrap_vshard_delay` (`number`, default: 5): delay before retry to bootstrap vshard;
* `cartridge_app_config` (`dict`): application config sections to patch;
* `cartridge_app_config_path` - path to application config to upload;
* `cartridge_app_config_upload_mode` - mode of config uploading (`lua`, `http` or `tdg`);
* `cartridge_app_config_upload_url` - url of instance to upload config
  (`http://127.0.0.1:{control_instance.http_port}/admin/config` by default);
* `cartridge_tdg_token` - token to upload config by HTTP in TDG;
* `cartridge_auth`: (`dict`): [authorization configuration](/doc/auth.md);
* `cartridge_failover_params` (`dict`): [failover](/doc/failover.md) parameters;
* [DEPRECATED] `cartridge_failover` (`boolean`): a boolean flag that
  indicates if eventual failover should be enabled or disabled;
* `cartridge_failover_promote_params` (`dict`): [failover promote](/doc/rolling_update.md#leaders-promotion) params.
* `wait_cluster_has_no_issues_retries` (`number`, default: 60): retries to check cluster has no issues;
* `wait_cluster_has_no_issues_delay` (`number`, default: 5): delay to retry cluster issues check;
* `allow_warning_issues` (`boolean`, default: `false`): allow issues with `warning` level.
* `show_issues`(`boolean`, default: `true`): - log cluster issues as a warnings.

## Eval step configuration

* `cartridge_eval_file` - path to file with Lua code to eval
  (isn't used if `cartridge_eval_body` is specified);
* `cartridge_eval_body` - code to eval;
* `cartridge_eval_args` - function arguments;
* `cartridge_eval_with_retries` - flag indicates that eval should be performed with retries;
* `cartridge_eval_retries` number of eval retries;
* `cartridge_eval_delay` - eval retries delay.

## Steps configuration

* `cartridge_delivered_package_path` - remote path to file of delivered package
  (use it to run `update_package` step without `deliver_package` step);
* `cartridge_control_instance` - some instance that can be used for editing
  topology and configuring cluster (use it to skip `set_control_instance` step).
