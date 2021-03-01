# Package

This role can work with RPM, DEB and [TGZ](/doc/tgz.md) packages created by
Tarantool Cartridge CLI.

You can specify a path to the application package `cartridge_package_path`.
Note, that package path shuold be the same for instances on one machine.

This role does not allow package downgrades because this may drive the cluster
inoperative.
If you are sure that you need to downgrade package, and you are aware of the risks,
you can perform this action manually
(for example, using Ansible
[yum](https://docs.ansible.com/ansible/latest/modules/yum_module.html) module).

