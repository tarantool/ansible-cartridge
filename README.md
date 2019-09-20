# Ansible Role: Tarantool Cartridge

An Ansible role to easily deploy [Tarantool Cartridge](https://github.com/tarantool/cartridge) applications.

This role can deploy and configure applications packed in RPM using [`Cartridge CLI`](https://github.com/tarantool/cartridge-cli).

## Table of contents

* [Requirements](#requirements)
* [Usage example](#usage-example)
* [Role variables](#role-variables)
* [Configuration format](#configuration-format)
  * [Instances configuration](#instances-configuration)
  * [Replicasets configuration](#replicasets-configuration)
  * [Vshard bootstrapping](#vshard-bootstrapping)
  * [Failover](#failover)

## Requirements

None.

## Usage example

Example cluster topology:

![image](https://user-images.githubusercontent.com/32142520/65237544-837dc580-dae3-11e9-97c6-db8676357eb5.png)

To deploy application and set up this topology:

`playbook.yml`:

```yaml
---
- name: Deploy my Tarantool Cartridge app
  hosts: all
  become: true
  become_user: root
  tasks:
  - name: Import Tarantool Cartridge role
    import_role:
      name: tarantool-cartridge
```

`hosts.yml`:

```yaml
---
all:
  hosts:
    vm1:
      ansible_host: 172.19.0.2  # First host
      ansible_user: vagrant

      cartridge_instances:  # Instances to be started on this host
        - name: 'core_1'
          advertise_uri: '172.19.0.2:3301'
          http_port: '8181'

        - name: 'storage_1'
          advertise_uri: '172.19.0.2:3302'
          http_port: '8182'

    vm2:
      ansible_host: 172.19.0.3  # Second host
      ansible_user: vagrant

      cartridge_instances:  # Instances to be started on this host
        - name: 'router'
          advertise_uri: '172.19.0.3:3303'
          http_port: '8183'

        - name: 'storage_1_replica'
          advertise_uri: '172.19.0.3:3304'
          http_port: '8184'


  vars:  # Cluster configuration
    cartridge_package_path: ./myapp-1.0.0-0.rpm  # Path to package to deploy

    cartridge_failover: true  # Enable automatic failover
    cartridge_bootstrap_vshard: true  # Bootstrap vshard

    cartridge_cluster_cookie: super-secret-cookie  # Cartridge cookie must be specified here
    cartridge_defaults:  # Default configuration parameters for all instances
      log_level: 5

    cartridge_replicasets:  # Replicasets to be set up
      - name: 'replicaset-1'
        instances:
          - 'storage_1'
          - 'storage_1_replica'
        leader: 'storage_1'
        roles: ['vshard-storage']

      - name: 'core-1'
        instances:
          - core_1
        roles: ['app.roles.custom']

      - name: 'router-1'
        instances:
          - router
        roles: ['vshard-router']
```

## Role variables

The role variables are used to configure started instances, cluster topology, vhsard bootstrapping and failover.

Configuration format is described in detail in the [configuration format](#configuration-format) section.

* `cartridge_package_path` (`string`, optional): path to Cartridge RPM package (application name will be detected as package name);
* `cartridge_app_name` (`string`): application name, required if `cartridge_package_path` is not specified;
* `cartridge_instances` (`list`, optional, default: `[]`): configuration for deployed instances;
* `cartridge_cluster_cookie` (`string`, required): cluster cookie for all cluster instances;
* `cartridge_defaults` (`dict`, optional, default: `{}`): default configuration parameters values for instances;
* `cartridge_replicasets` (`list`, optional, default: `[]`) - replicasets configuration;
* `cartridge_bootstrap_vshard` (`boolean`, optional, default: `false`): boolean flag that indicates if vshard should be bootstrapped;
* `cartridge_failover` (`boolean`, optional, default: `false`): boolean flag that indicates if failover should be enabled.

**Note**: If instance is menitioned in `cartridge_replicasets` section, it should be configured in `cartridge_instances`.

## Configuration format

Instances and replicasets are identified by names, so you must use unique names to aviod collisions.

### Application

You can specify path to rpm package to be installed using `cartridge_package_path`. In this case `cartridge_app_name` will be rewrited by package name from rpm info.

But if you don't specify rpm package path (for example, you have already installed rpm, and now you just want to start instances or configure replicasets), you should specify `cartridge_app_name`.

### Instances

Each instance of application is started as `<app_name>@<instance_name>` systemd service.

It can be configured using the `cartridge_instances` variable. 
This variable describes all instances that should be deployed on the host.

`cartridge_instances` is a list of dicts that contains  [cluster-specific](https://www.tarantool.io/en/rocks/cartridge/1.0/modules/cartridge.argparse/#cluster-opts) parameters or some application-specific parameters (can be parsed in application using the [`cartridge.argparse`](https://www.tarantool.io/en/rocks/cartridge/1.0/modules/cartridge.argparse) module).

**Required instance parameters**: `name`, `advertise_uri`, `http_port`.

**Note:** It's recommended to specify both host and port for the `advertise_uri` parameter.
If your deploy host has more than one non-local IP address, advertise host will be set to `localhost`.

**Note:** If instance with the same name is already started on the host, it will be restarted with new configuration. 

### Replicasets

Cluster topology can be configured using `cartridge_replicasets` variable (must be placed in `all` group).

`cartridge_replicasets` is a list of `replicaset` dicts:

* `replicaset.name` (`string`, required) - name of replicaset, will be displayed in Web UI;
* `replicaset.instances` (`list-of-strings`, required) - names of instances, which must be joined to replicaset;
* `leader` (`string`) - name of leader instance. Optional if replicaset contains only one instance, required for replicaset with more than one instances;
* `roles` (`list-of-strings`, required) - roles to be enabled on the replicaset.

**Note**: Replicaset would be set up **only** if replicaset with the same name is not set up yet.

**Note**: If instance is menitioned in `cartridge_replicasets` section, it should be configured in `cartridge_instances`.

### Vshard bootstrapping

Flag `cartridge_bootstrap_vshard` indicates if vshard must be bootstrapped on cluster.

First, it would be checked if it is reasonble to bootstrap VShard (cluster must have at least one `vshard-storage` replicaset and at least one `vshard-router`).
If it is, VShard will be bootstrapped.

### Failover

If `cartridge_bootstrap_vshard` is `true`, then failover will be enabled.
