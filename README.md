# Ansible Role: Tarantool Cartridge

[![Ansible Galaxy](https://img.shields.io/github/v/release/tarantool/ansible-cartridge?include_prereleases&labelColor=2d3532&color=27c24c)](https://galaxy.ansible.com/tarantool/cartridge)
[![Unit tests](https://github.com/tarantool/ansible-cartridge/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/tarantool/ansible-cartridge/actions/workflows/unit-tests.yml)
[![Molecule tests](https://github.com/tarantool/ansible-cartridge/actions/workflows/molecule-tests.yml/badge.svg)](https://github.com/tarantool/ansible-cartridge/actions/workflows/molecule-tests.yml)
[![Consistency tests](https://github.com/tarantool/ansible-cartridge/actions/workflows/consistency-tests.yml/badge.svg)](https://github.com/tarantool/ansible-cartridge/actions/workflows/consistency-tests.yml)

An Ansible role to easily deploy
[Tarantool Cartridge](https://github.com/tarantool/cartridge) applications.

This role can deploy and configure applications packed in `RPM`, `DEB` and `TGZ` using
[`Cartridge CLI`](https://github.com/tarantool/cartridge-cli).

Only `RedHat` and `Debian` OS families are supported.

## Table of contents

* [Requirements](#requirements)
* [Installation](#installation)
* [Quick start](#quick-start)
* [Using scenario](#using-scenario)
* [Documentation](#documentation)
* [Cookbook](#cookbook)

## Requirements

* Tarantool Cartridge >= 2.0.0, < 3;
* Ansible 2.8.4 or higher.

Note that running the role may require
[root access](https://docs.ansible.com/ansible/2.4/become.html).

## Installation

First, you need to install this role using `ansible-galaxy`:

```bash
$ ansible-galaxy install tarantool.cartridge,1.10.0
```

## Quick start

Check out the [Getting Started guide](/cookbook/getting-started)
to learn how to use this role.

You can start two virtual machines using example
[Vagrantfile](/doc/files/Vagrantfile).

Let's deploy an application with simple topology.

First, pack your application to RPM using `cartridge pack rpm` command.

Then, describe the topology in `hosts.yml` file:

`hosts.yml`:

```yaml
---
all:
  vars:
    cartridge_app_name: myapp
    cartridge_package_path: ./myapp-1.0.0-0.rpm
    cartridge_cluster_cookie: secret-cookie

    # may be useful for vagrant
    ansible_ssh_private_key_file: ~/.vagrant.d/insecure_private_key
    ansible_ssh_common_args: '-o IdentitiesOnly=yes -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'

  hosts:
    storage-1:
      config:
        advertise_uri: '172.19.0.2:3301'
        http_port: 8181

    storage-1-replica:
      config:
        advertise_uri: '172.19.0.2:3302'
        http_port: 8182

  children:
    # group instances by machines
    machine_1:
      vars:
        # first machine address and connection opts
        ansible_host: 172.19.0.2
        ansible_user: vagrant

      hosts:  # instances to be started on this machine
        storage-1:
        storage-1-replica:

    # group instances by replicasets
    storage_1_replicaset:  # replicaset storage-1
      hosts:  # instances
        storage-1:
        storage-1-replica:
      vars:
        # replicaset configuration
        replicaset_alias: storage-1
        roles:
          - 'vshard-storage'
        failover_priority:
          - storage-1
          - storage-1-replica
```

Write a simple playbook that imports role:

```yaml
# playbook.yml
---
- name: Deploy my Tarantool Cartridge app
  hosts: all
  become: true
  become_user: root
  any_errors_fatal: true
  gather_facts: false
  roles:
    - tarantool.cartridge
```

Then run the playbook with created inventory:

```bash
ansible-playbook -i hosts.yml playbook.yml
```

Now, visit http://localhost:8181

![image](/doc/images/quck-start.png)

## Using scenario

It's possible to perform different actions with instances or replicasets
by combining [`cartridge_scenario`](/doc/scenario.md) variable and Ansible limits.

For example, you can configure and start some instances.
To do this, you should define `cartridge_scenario` variable like this:

```yaml
cartridge_scenario:
  - configure_instances
  - start_instance
  - wait_instance_started
```

Then run playbook with `--limit` option:

```bash
ansible-playbook -i hosts.yml playbook.yml --limit instance_1,instance_2
```

You can also simply edit some replicaset.
To do this, define `cartridge_scenario` variable like this:

```yaml
cartridge_scenario:
  - edit_topology
```

After run playbook with `--limit` option:

```bash
ansible-playbook -i hosts.yml playbook.yml --limit replicaset_1_group,replicaset_2_group
```

Moreover, scenario allows you to describe custom steps for configuring cluster.
For more details about using scenario and available steps, see
[scenario documentation](doc/scenario.md).

## Documentation

* [Configuration basics](/doc/configuration-basics.md)
* [Role variables](/doc/variables.md)
* [Role scenario](/doc/scenario.md)
* [Role steps description](/doc/steps.md)
* [Application package](/doc/package.md)
* [Deploying TGZ package](/doc/tgz.md)
* [Using multiversion approach](/doc/multiversion.md)
* [Configuring instances](/doc/instances.md)
* [Configuring topology](/doc/topology.md)
* [VShard bootstrapping](/doc/vshard_bootstrapping.md)
* [Configuring auth](/doc/auth.md)
* [Configuring failover](/doc/failover.md)
* [Configuring stateboard](/doc/stateboard.md)
* [Application config](/doc/app_config.md)
* [Rolling update](/doc/rolling_update.md)
* [Eval Lua code on instances](/doc/eval.md)

## Cookbook

Learn [the cookbook](/cookbook/README.md) to know now to use the
`tarantool.cartridge` role for different purposes.
