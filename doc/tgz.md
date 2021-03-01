# Managing TGZ package

Deploying TGZ archive is different from deploying RPM or DEB.
It requires additional actions such as configuring systemd units.
All these actions can be disabled.

Using TGZ package allows to use [multiversion approach](./multiversion.md)
that can be helpful to perform rolling update correclty.
This approach uses links to specify version of application that is used by each
instance.

## Unpacking TGZ

TGZ package contains one directory named `cartridge_app_name` that contains application files.
By default, it is unpacked to `cartridge_app_install_dir` directory according to
[multiversion](./multiversion.md) policy.

### Installing Tarantool

If package doesn't contain `tarantool` binary, opensource Tarantool is installed.
It's version is described in `VERSION` file that is created by Cartridge CLI
on application packing.

Use `cartridge_install_tarantool_for_tgz` flag to disable installation
of Tarantool.

### Application user ang group

Application user that owns all application files and instances processes
can be configured using `cartridge_app_user` and `cartridge_app_group` variables.

### Application directories

Application directories are created before unpacking.
To configure them use

* `cartridge_data_dir`
* `cartridge_run_dir`
* `cartridge_conf_dir`
* `cartridge_app_install_dir`
* `cartridge_app_instances_dir` in case of using [multiversion](./multiversion.md)

### `systemd` unit files

Systemd unit files for application instances and stateboard are
created in `cartridge_systemd_dir`.

Use `cartridge_configure_systemd_unit_files` flag to disable configuring systemd
unit files.

### Configuring tmpfiles

To prevent removing `cartridge_run_dir` (that is placed in `/var/run` by default)
after machine restart application needs tmpfiles configuration.
It's placed in `cartridge_tmpfiles_dir`.

Use `cartridge_configure_tmpfiles` flag to disable configuring tmpfiles.
