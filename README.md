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
  * [Cartridge auth](#cartridge-auth)
  * [Application config](#applicaction-config)

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
      ansible_host: 172.19.0.2  # first host
      ansible_user: vagrant

      cartridge_instances:  # instances to be started on this host
        - name: 'core_1'
          advertise_uri: '172.19.0.2:3301'
          http_port: '8181'

        - name: 'storage_1'
          advertise_uri: '172.19.0.2:3302'
          http_port: '8182'

    vm2:
      ansible_host: 172.19.0.3  # second host
      ansible_user: vagrant

      cartridge_instances:  # instances to be started on this host
        - name: 'router'
          advertise_uri: '172.19.0.3:3303'
          http_port: '8183'

        - name: 'storage_1_replica'
          advertise_uri: '172.19.0.3:3304'
          http_port: '8184'


  vars:  # cluster configuration
    cartridge_package_path: ./myapp-1.0.0-0.rpm  # path to package to deploy

    cartridge_failover: true  # enable automatic failover
    cartridge_bootstrap_vshard: true  # bootstrap vshard

    cartridge_cluster_cookie: super-secret-cookie  # cartridge cookie must be specified here
    cartridge_defaults:  # default configuration parameters for all instances
      log_level: 5

    cartridge_replicasets:  # replicasets to be set up
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
* `cartridge_failover` (`boolean`, optional): boolean flag that indicates if failover should be enabled or disabled;
* `cartridge_app_config` (`dict`, optional): application config sections to patch.

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

**Required instance parameters**: `name`, `advertise_uri`.

**Note:** `advertise_uri` parameter must be specified in `<host>:<port>` format.

**Note:** If instance with the same name is already started on the host, it will be restarted with new configuration. 

### Replicasets

Cluster topology can be configured using `cartridge_replicasets` variable (must be placed in `all` group).

`cartridge_replicasets` is a list of replicaset configurations:

* `name` (`string`, required) - name of replicaset, will be displayed in Web UI;
* `instances` (`list-of-strings`, required) - names of instances, which must be joined to replicaset;
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

### Cartridge auth

`cartridge_auth` parameter is used to specify authorization parameters:

- `enabled`(`boolean`, optional) - indicates if authentication must be enabled;
- `cookie_max_age`(`int`, optional) - number of seconds until the authentication cookie expires;
- `cookie_renew_age`(`int`, optional) - update provided cookie if it's older then this age.
- `users`(`list-of-dicts`, optional) - list of users to be configured on cluster (described below).

**Users configuration:**

- `username`(`string`, required);
- `password`(`string`, optional) - is required for new users;
- `fullname`(`string`, optional);
- `email`(`string`, optional);
- `deleted`(`boolean`, optional) - indicates if user must be removed.

**Note:** Default user `admin` can't be managed here.

*Example:*

```yaml
cartridge_auth:
  enabled: true   # enable authorization

  cookie_max_age: 1000
  cookie_renew_age: 100

  users:  # cartridge users to be set up
    - username: tarantool
      password: tarantool-the-best
      fullname: Tarantool The Best
      email: tarantool@tarantool.org

    - username: bad-guy
      deleted: true  # marked to be deleted
```

### Applicaction config

`cartridge_app_config` variable is used to edit cluster configuration.
It allows to configure config sections in special format:

```yaml
cartridge_app_config:
  <section_name>:
    body: <section body>
    deleted: <boolean>
```


- sections with `deleted` flag set up would be deleted;
- sections not mentioned here wouldn't be changed;
- other sections value would be replaced with section `body` value.

*Example*

If your cluster config looks like:

```yaml
section-1: value-1  # section body is a string

section-2:  # section body is a table
  key-21: value-21
  key-22: value-22

section-3:
  key-31: value-31
```

... after running role with this `cartridge_app_config`:

```yaml
cartridge_app_config:
  section-2:
    body:
      key-21: value-21-new

  section-3:
    deleted: true
```

... it would be

```yaml
section-1: value-1  # hasn't been changed

section-2:
  key-21: value-21-new  # body was replaced
```
