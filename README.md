# Ansible Role: Tarantool Cartridge

An Ansible role to easily deploy
[Tarantool Cartridge](https://github.com/tarantool/cartridge) applications.

This role can deploy and configure applications packed in RPM using
[`Cartridge CLI`](https://github.com/tarantool/cartridge-cli).

<!-- ## Table of contents

* [Usage](#usage)
* [Requirements](#requirements)
* [Usage example](#usage-example)
* [Getting started](#getting-started)
* [Role variables](#role-variables)
* [Configuration format](#configuration-format)
  * [Instances](#instances)
  * [Replica sets](#replica-sets)
  * [Vshard bootstrapping](#vshard-bootstrapping)
  * [Failover](#failover)
  * [Cartridge authorization](#cartridge-authorization)
  * [Application configuration](#application-configuration) -->


<!-- ## Requirements

* Tarantool Cartridge 1.2.0 or higher;
* Ansible 2.8.4 or higher. -->

## Usage example

<!-- Example cluster topology:

![image](https://user-images.githubusercontent.com/32142520/65237544-837dc580-dae3-11e9-97c6-db8676357eb5.png)

To deploy an application and set up this topology: -->

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
  children:
    cluster:  # cluster configuration
      vars:
        cartridge_package_path: ./myapp-1.0.0-0.rpm
        cartridge_cluster_cookie: secret-cookie
        cartridge_defaults:
          log_level: 1

      children:
        # group instances by machines
        host1:
          vars:
            # vm1 machine addres and connection opts
            ansible_host: vm1
            ansible_user: root
            ansible_connection: docker
            become: true
            become_user: root

          hosts:  # instances to be started on this host
            storage-1:
              config:
                advertise_uri: 'vm1:3301'
                http_port: 8081

            storage-1-replica:
              config:
                advertise_uri: 'vm1:3302'
                http_port: 8082

        host2:
          vars:
            # vm2 machine addres and connection opts
            ansible_host: vm2
            ansible_user: root
            ansible_connection: docker
            become: true
            become_user: root

          hosts:  # instances to be started on this host
            core-1:
              config:
                advertise_uri: 'vm2:3311'
                http_port: 8091

            storage-1-replica-2:
              config:
                advertise_uri: 'vm2:3312'
                http_port: 8092

        # group instances by replicasets
        storage_1_replicaset:  # replicaset storage-1
          hosts:  # instances
            storage-1:
            storage-1-replica:
            storage-1-replica-2:
          vars:
            # replicaset configuration
            replicaset_name: storage-1
            leader: storage-1
            roles:
              - 'vshard-storage'

        core_1_replicaset:  # replicaset core-1
          hosts:  # instances
            core-1:

          vars:
            # replicaset configuration
            replicaset_name: core-1
            leader: core-1
            roles:
              - 'app.roles.custom'
              - 'vshard-router'
```

### Tags

* `cartridge-instances` - install package, update instances config and restart instances;
* `cartridge-replicasets` - configure replicasets.

### Run all tasks for all hosts

```bash
ansible-paymook -i hosts.yml playbook.yml
```

### Run tasks only for two instances

Could be useful for restarting a few instances.

Set up replicasets after instances restart:

```bash
ansible-paymook -i hosts.yml playbook.yml \
                --limit core-1,storage-1
```

Restart only two instances and don't configure replicasets:

```bash
ansible-paymook -i hosts.yml playbook.yml \
                --limit core-1,storage-1 \
                --tags cartridge-instances
```

### Run tasks only for instances on one host

```bash
ansible-paymook -i hosts.yml playbook.yml \
                --limit host1
```

### Run tasks only for instances from one replicaset

```bash
ansible-paymook -i hosts.yml playbook.yml \
                --limit storage_1_replicaset
```

### Join one replicaset, don't configure instances

```bash
ansible-paymook -i hosts.yml playbook.yml \
                --limit storage_1_replicaset \
                --tags cartridge-replicasets
```

<!-- 
## Getting started

See the [getting started guide](./examples/getting-started-app/README.md)
to learn how to set up topology using this role.

## Role variables

Role variables are used to configure started instances, cluster topology,
vhsard bootstrapping, and failover.

Configuration format is described in detail in the
[configuration format](#configuration-format) section.

* `cartridge_package_path` (`string`, optional): path to Cartridge RPM package
  (application name will be detected as package name);
* `cartridge_app_name` (`string`): application name, required if
  `cartridge_package_path` is not specified;
* `cartridge_instances` (`list`, optional, default: `[]`): configuration for
  deployed instances;
* `cartridge_cluster_cookie` (`string`, required): cluster cookie for all
  cluster instances;
* `cartridge_defaults` (`dict`, optional, default: `{}`): default configuration
  parameters values for instances;
* `cartridge_replicasets` (`list`, optional, default: `[]`) - replica sets
  configuration;
* `cartridge_bootstrap_vshard` (`boolean`, optional, default: `false`): boolean
  flag that indicates if vshard should be bootstrapped;
* `cartridge_failover` (`boolean`, optional): boolean flag that indicates if
  failover should be enabled or disabled;
* `cartridge_app_config` (`dict`, optional): application config sections to patch;
* `cartridge_enable_tarantool_repo` (`boolean`, optional, default: `true`):
  indicates if the Tarantool repository should be enabled (for packages with
  open-source Tarantool dependency).

**Note**: If an instance is mentioned in the `cartridge_replicasets` section,
it should be configured in `cartridge_instances`.

## Configuration format

Instances and replica sets are identified by names, so you must use unique names
to avoid collisions.

### Application

You can specify path to the rpm package to be installed using
`cartridge_package_path`. In this case `cartridge_app_name` will be rewritten
by the package name from rpm info.

But if you specify no rpm package path (for example, you have already installed
rpm, and now you just want to start instances or configure replica sets), you
should specify `cartridge_app_name`.

### Instances

Each instance of the application is started as `<app_name>@<instance_name>`
systemd service.

It can be configured using the `cartridge_instances` variable.
This variable describes all instances that should be deployed on the host.

`cartridge_instances` is a list of dicts that contains
[cluster-specific](https://www.tarantool.io/en/rocks/cartridge/1.0/modules/cartridge.argparse/#cluster-opts)
parameters or some application-specific parameters (can be parsed in application
using the [`cartridge.argparse`](https://www.tarantool.io/en/rocks/cartridge/1.0/modules/cartridge.argparse)
module).

#### Required parameters

`name` and `advertise_uri` are required parameters for an instance.

**Notes:**
* `name` will be used for systemd service name and instance alias.
* `advertise_uri` parameter must be specified in the `<host>:<port>` format.
* If an instance with the same name is already started on the host, it will be
  restarted with new configuration.

#### Forbidden parameters

`alias`, `console_sock`, `pid_file`, and `workdir` parameters are forbidden
for an instance.

Instance alias will be set equal to instance name.

**Note:** in the default systemd unit file for Tarantool Cartridge applications,
some instance parameters are set:

```
Environment=TARANTOOL_WORKDIR=/var/lib/tarantool/{app_name}.{instance_name}
Environment=TARANTOOL_CFG=/etc/tarantool/conf.d/
Environment=TARANTOOL_PID_FILE=/var/run/tarantool/${app_name}.{instance_name}.pid
Environment=TARANTOOL_CONSOLE_SOCK=/var/run/tarantool/${app_name}.{instance_name}.control
```

### Replica sets

Cluster topology can be configured using the `cartridge_replicasets` variable
(must be placed in `all` group).

`cartridge_replicasets` is a list of replica set configurations:

* `name` (`string`, required) - name of the replica set, will be displayed in
  the Web UI;
* `instances` (`list-of-strings`, required) - names of instances, which must be
  joined to the replica set;
* `leader` (`string`) - name of the leader instance. Optional if the replica set
  contains only one instance, required for a replica set with more than one
  instance;
* `roles` (`list-of-strings`, required) - roles to be enabled on the replica set.

**Note**:
* A replica set will be set up **only** if a replica set with the same
  name is not set up yet.
* If an instance is mentioned in the `cartridge_replicasets` section, it should
  be configured in `cartridge_instances`.

### Vshard bootstrapping

The flag `cartridge_bootstrap_vshard` indicates if vshard must be bootstrapped
on the cluster.

First, it will be checked if it is reasonable to bootstrap vshard (the cluster
must have at least one `vshard-storage` replica set and at least one
`vshard-router`). If it is, vshard will be bootstrapped.

### Failover

If `cartridge_bootstrap_vshard` is `true`, then failover will be enabled.

### Cartridge authorization

`cartridge_auth` parameter is used to specify authorization settings:

- `enabled`(`boolean`, optional) - indicates if authorization is enabled;
- `cookie_max_age`(`int`, optional) - number of seconds until the authorization
  cookie expires;
- `cookie_renew_age`(`int`, optional) - update the provided cookie if it's older
  than this age.
- `users`(`list-of-dicts`, optional) - list of users to be configured on the
  cluster (described below).

**Users configuration:**

- `username`(`string`, required);
- `password`(`string`, optional) - is required for new users;
- `fullname`(`string`, optional);
- `email`(`string`, optional);
- `deleted`(`boolean`, optional) - indicates if the user must be removed.

**Note:** The default user `admin` can't be managed here.

*Example:*

```yaml
cartridge_auth:
  enabled: true   # enable authorization

  cookie_max_age: 1000
  cookie_renew_age: 100

  users:  # cartridge users to set up
    - username: tarantool
      password: tarantool-the-best
      fullname: Tarantool The Best
      email: tarantool@tarantool.org

    - username: bad-guy
      deleted: true  # marked to be deleted
```

### Application configuration

`cartridge_app_config` variable is used to edit cluster configuration.
It allows to define configuration sections in a special format:

```yaml
cartridge_app_config:
  <section_name>:
    body: <section body>
    deleted: <boolean>
```
**Note:**
* sections with the `deleted` flag set up will be deleted;
* sections not mentioned here won't be changed;
* other sections values will be replaced with the section `body` value.

*Example*

If your cluster configuration looks like:

```yaml
section-1: value-1  # section body is a string

section-2:  # section body is a table
  key-21: value-21
  key-22: value-22

section-3:
  key-31: value-31
```

... after running a role with this `cartridge_app_config`:

```yaml
cartridge_app_config:
  section-2:
    body:
      key-21: value-21-new

  section-3:
    deleted: true
```

... it will be:

```yaml
section-1: value-1  # hasn't been changed

section-2:
  key-21: value-21-new  # body was replaced
``` -->
