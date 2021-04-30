# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]
<!--
Please update `ansible-galaxy install` command in
README.md to use the newest tag with new release
-->

## [1.9.0] - 2021-04-30

### Fixed

- Running the role with python 2.7
- Skipping instances restart when package was updated, but configuration wasn't
- Missing default config for machine with stateboard
- Specifying `cartridge_app_name` other than the TGZ package name
- Creating unnamed replicasets with instances without `replicaset_alias` set
- Getting control instance:
  - Now one not expelled instance should also be alive; it's checked
    by creating connection using instances advertise URIs
  - Control instance should be alive
  - If there are some joined instances, but no one of them isn't alive,
    getting control instance fails.
- `set_control_instance` is improved to consider non-joined instance status
- `edit_topology` step now considers roles dependencies, permanent and hidden roles
  and don't perform unnecessary calls if enabled roles list isn't changed

### Added

- `failover_promote` step to promote replicasets leaders
- Allowed to skip user and group creation for tgz
- Debug control instance and one not expelled instance
- Timeouts for two-phase commits:
  * `twophase_netbox_call_timeout`
  * `twophase_upload_config_timeout`
  * `twophase_apply_config_timeout`
- `eval` and `eval_on_control_instance` steps to eval code on instances
- Step `stop_instance` to stop and disable instance systemd service
- Step `start_instance` to start and enable instance systemd service
- Step `restart_instance_force` to restart systemd service without any conditions
- New `cartridge_failover_params` fields:
  - `failover_timeout`
  - `fencing_enabled`
  - `fencing_timeout`
  - `fencing_pause`
- `edit_topology_allow_missed_instances` variable to allow replicasets containing
  the instances that are not started yet
- `upload_app_config` step to load the file or directory config
  (Cartridge and TDG are supported)

### Changed

- Timeout to wait for cluster health after topology editing
  renamed from `edit_topology_timeout` to `edit_topology_healthy_timeout`
- `cartridge_cluster_cookie` now is required only for `configure_instance`,
  `restart_instance` and `upload_app_config` steps

## [1.8.3] - 2021-04-06

### Changed

- Now only the necessary information will be transferred in tasks,
  which used `hostvars`. Due to this duration of these tasks was reduced.

### Fixed

- Role variables are saved to the dictionary, so they do not affect the next play

## [1.8.2] - 2021-04-01

### Fixed

- Fix facts setting in `hostvars` fact
- Avoid using the `non_expelled_instance` fact name.
  Now the `not_expelled_instance` name is used everywhere.

## [1.8.1] - 2021-03-31

### Fixed

- Removing stateboard instance distribution directory on `rotate_dists` step
- Fixed fail on getting one non-expelled instance when only stateboard instance
  is configured
- Fixed compatibility with Ansible 2.9

## [1.8.0] - 2021-03-23

### Fixed

- Role installation will be completely skipped
  if you specify a tag other than the tags for this role
- Fixed selecting control instance that doesn't belong to cluster or isn't alive.
  The following rules are currently used:
  * Members are checked in lexicographic order by URIs
  * Members not mentioned in hostvars aren't selected to be control
  * Members with status not `alive` aren't selected to be control
- Fixed setting `needs_restart` when configuration files don't exist
- Fixed error on configuring auth without users specified
- Reset role variables before each run

### Added

- `cartridge-replicasets` tag to the membership stage
- `cartridge_wait_buckets_discovery` parameter to wait for instance to discover buckets
- `instance_discover_buckets_timeout` parameter to configure time in seconds
  to wait for instance to discover buckets
- Ability to deploy TGZ packages
- `cartridge_multiversion` flag that allows to use specific version of application
  for each instance and perform rolling update correctly (using new `update_instance` step)
- `rotate_dists` step that allows to rotate application distributions
- `cleanup` step to remove temporary files from specific list
- Added availability to import steps by scenario name. Added some default scenarios.
  Added availability to create custom scenarios.
- availability to use `tasks_from` to import any step
- `zone` variable to edit instance zone
- `edit_topology_timeout` variable to wait until cluster become healthy
  after editing topology
- availability to specify instance `memtx_dir`, `vinyl_dir` and `wal_dir` params
  by `cartridge_memtx_dir_parent`, `cartridge_vinyl_dir_parent`, `cartridge_wal_dir_parent` variables.
- Control instance is selected considering two-phase commit version of instances.
  The reason is that all operations that modify cluster-wide config should be performed via instance
  that has lowest Cartridge version (in fact, only two-phase commit version matters).
- Availability to change advertise URIs of any instance

### Changed

- `cartridge.admin_edit_topology` is called once for all replicasets and instances
  to expel. It can be called second time to set up failover priority for
  replicasets where new instances were joined.
  As a result, `replicaset_healthy_timeout` is removed as unused.
- Now list of instances for installing a package is selected once for all.
  Before this patch, the complexity of calculating the list of instances was O(N^2),
  now it is O(N). For 100 instances, it gives a 10x time reduction (60s -> 5s).
- Refactored package installing. Getting package info is performed in a library module,
  all tasks except installing package itself are common for RPM and DEB.
- Now `check_instance_started` function: check all instances, including the stateboard;
  wait `Unconfigured` or `RolesConfigured` status instead `alive` state; check that
  all buckets are discovered by routers if cluster was bootstrapped.
- Role divided into many steps (#141). It's possible to combine them using a scenario
  in the config by `cartridge_scenario`. It is also possible to use custom steps in a scenario.
  Custom steps can be defined by `cartridge_custom_steps_dir` and `cartridge_custom_steps`.
- Now step `connect_to_membership` is executed only on one not expelled instance.
  Before the patch, the difficulty of performing `connect_to_membership` step was `N^2`.
  For 100 instances, the step took about 900 seconds. Now the complexity has decreased to N,
  so for 100 instances the execution time is about 5 seconds.

## [1.7.0] - 2020-11-24

### Fixed

- needs_restart task error for non-bootstrapped instance

### Added

- `replicaset_healthy_timeout` parameter to wait for replicaset to be
  healthy after editing it

## [1.6.0] - 2020-11-10

### Added

- Managing dynamic `box.cfg` parameters in runtime

## [1.5.0] - 2020-10-06

### Added

- `restarted: false` to disable instance restart

## [1.4.0] - 2020-07-15

### Added

- `etcd2` state provider for stateful failover (cartridge >= 2.2.0)

## [1.3.0] - 2020-05-08

### Added

- `cartridge_failover_params` variable to manage new failover (cartridge >= 2.1.0)
- `stateboard` flag to start Tarantool Stateboard instance (cartridge >= 2.1.0)

### Changed

- `any_errors_fatal: true` is set for package installation tasks
- `falover_priority` parameter is optional

### Deprecated

- `cartridge_failover` variable

## [1.2.0] - 2020-04-08

### Fixed

* Liitle bugs in python modules

## [1.1.0] - 2020-01-29

### Added

* `vshard_group` parameter for `vshard-storage` replicasets

## [1.0.4] - 2020-01-22

### Added

* Cluster cookie checks

## [1.0.3] - 2020-01-09

### Changed

* `ansible_host` value is used as an unique host identifier
  instead of `ansible_machine_id`
* `cartridge_app_name` is checked to be equal to package name
   on package installation

## [1.0.2] - 2019-12-18

### Fixed

* Error on control instance selection

## [1.0.1] - 2019-12-03

### Added

* Store error codes in CartridgeException
* Interpret some errors as a valid behaviour in cartridge_needs_restart and
  cartridge_instance modules

### Fixed

* Do not try to manage memtx_memory in runtime for expelled
* Fixed "Unable to patch config system section" errmsg

## [1.0.0] - 2019-11-25

### Added

* Increasing memtx_memory without instance restart
* `restarted` flag to force instance restart
* `expelled` flag to expel instance from cluster
* `weight` and `all_rw` replicaset parameters
* Editing existed replicaset
* Tests for debian
* `instance_start_timeout` parameter to wait for instance to be started

### Changed

* `leader` parameter replaced by `failover_priority`
* Use `cartridge.admin_edit_topology()` call to manage topology
* Test inventory restructured
* Added retry on Vshard bootstrapping
* `cartridge_app_name` parameter is mandatory now and it isn't rewrited by package info
* Installing package tasks are running for one non-expelled instance per machine

### Fixed

* Added missed tags for start_instance tasks
* Fix endless loop for recvall() in case of broken pipe
* Fixed KeyError on joining not started instance to replicaset

## [0.2.0] - 2019-11-14

### Changed

* Configure cluster using tarantool console socket instead of HTTP
* Improved Gitlab CI test packages creation
* Use both deb and rpm packages in molecule tests
* Variables structure is changed to interpret instances as Ansible hosts
* Instance connects to membership by probing other instances

### Fixed

* Removed `cartridge_failover` default value
* Removed useless unzip installation
* Console eval fixed to find end of output using full ouput data

### Added

* DEB packages deployment
* Reloading systemd daemon after package updating
* Getting started

## [0.1.0] - 2019-10-01

### Added

* RPM packages deployment
* instances configuration and starting
* topology configuration
* vhard bootstrapping
* managing failover
* authorization configuration
* molecule tests
* application config patching
