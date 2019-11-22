# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
