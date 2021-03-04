# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]
<!--
Please update `ansible-galaxy install` command in
README.md and examples/getting-started-app/README.md
to use the newest tag with new release
-->

### Fixed

- Role installation will be completely skipped
  if you specify a tag other than the tags for this role

### Added

- `cartridge-replicasets` tag to the membership stage
- `cartridge_wait_buckets_discovery` parameter to wait for instance to discover buckets
- `instance_discover_buckets_timeout` parameter to configure time in seconds
  to wait for instance to discover buckets
- `rotate_dists` step that allows to rotate application distributions

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
