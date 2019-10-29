# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

* Configure cluster using tarantool console socket instead of HTTP
* Improved Gitlab CI test packages creation
* Use both deb and rpm packages in molecule tests

### Fixed

* Removed `cartridge_failover` default value
* Removed useless unzip installation
* Console eval fixed to find end of output using full ouput data

### Added

* DEB packages deployment
* Reloading systemd daemon after package updating

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
