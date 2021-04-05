# Configuration basics

This topic describes basics of inventory that help you to understand the
way it works.

It also describes configuring instances and replicasets for managing Tarantool
Cartridge-based applications.

## Inventory format

**Note**, that inventory can be described in a different ways, this guide
describes only one of them - YAML file.

Generally, inventory operates groups of hosts.
There are two [default groups](https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html#default-groups):
`all` and `ungrouped`.
The `all` group contains every host.

**Note**, that we use "host" word for instances, i.e. nodes of infrastructure.
For machines where hosts (instances) are placed "machine" word is used.

To configure instance Ansible should connect to it.
It means that for each instance we should specify connection options.
The simplest way to do it - use groups.

Our inventory starts with `all` group definition.
Group is a dictionary with these keys allowed:

* `vars` - variables common for all hosts in this group;
* `hosts` - hosts that belong to this group;
* `children` - sub-group of current group.

We use groups to pass common variables for several instances.
For example, each instance should know application name.
Is't much easier to write that `all` instances have some application name
then to write that **every** instance has some application name.

## Variables priority

Let's look at this simplest inventory file:

```yaml
---
all:
  vars:
    colour: common-colour
  hosts:
    instance_common:
    instance_blue_1:
    instance_blue_2:
    instance_fake_blue:
    instance_red_1:
    instance_with_own_colour:
      colour: my-own-colour
  children:
    blue:
      hosts:
        instance_blue_1:
        instance_blue_2:
        instance_fake_blue:
          colour: yellow-colour
      vars:
        colour: blue-colour

    red:
      hosts:
        instance_red_1:
      vars:
        colour: red-colour
```

* `instance_common` uses colour value for group `all` - `common-colour`;
* `instance_blue_1` and `instance_blue_2` uses colour value specific for
  group `blue` - `blue-colour`;
* `instance_fake_blue` also belongs to `blue` grop, but it also have it's own
  colour value set - ` yellow-colour`;
* `instance_red_1` uses colour value specific for
  group `red` - `red-colour`;
* `instance_with_own_colour` has it's own colour value set - `my-own-colour`;

## Configuring instances and replica sets

The common cases to use groups with `tarantool.cartridge` role are:

* set connection options for instances deployed on one machine;
* set replicaset options for instances from one replicaset.

What should you understand to configure instances:

* each instance is an Ansible host;
* the hostname is instance alias that is used by role to identify instance.

### Instances

Imagine that you want to deploy three instances:

* `core-1`
* `storage-1-leader`
* `storage-1-replica`

For each instance we should specify following [variables](/doc/variables.md):
* `cartridge_app_name`
* `cartridge_cluster_cookie`
* `cartridge_package_path`
* `config`

`config` variable is specific for each instance, other variables are common
and can be placed in `all` group.

Let's begin:

```yaml
---
all:
  vars:
    cartridge_app_name: myapp
    cartridge_cluster_cookie: secret-cookie
    cartridge_package_path: ./myapp-1.0.0-0.rpm

  hosts:
    core-1:
      config:
        advertise_uri: '172.19.0.2:3301'

    storage-1-leader:
      config:
        advertise_uri: '172.19.0.2:3302'

    storage-1-replica:
      config:
        advertise_uri: '172.19.0.3:3301'
```

We've just declared three hosts (i.e. nodes that we want to configure),
set common configuration parameters and parameters specific for each instance.

But how should Ansible understand where each instance should be started?

### Connection options

As you can understand by looking at advertise URIs, instances are placed on two machines:

* `machine_1` (`172.19.0.2`):
  * `core-1`
  * `storage-1-leader`

* `machine_2` (`172.19.0.3`):
  * `storage-1-replica`

For each instance we should describe connection options:

* `ansible_host` - IP or name of the machine where instance should be placed;
* `ansible_user` - the user Ansible "logs in" as.

We will use `groups` to specify options common for several instances:

```yaml
all:
  vars:
    ...
  hosts:
    ...
  children:
    machine_1:
      vars:
        ansible_host: 172.19.0.2
        ansible_user: vagrant

      hosts:
        core-1:
        storage-1-leader:

    machine_2:
      vars:
        ansible_host: 172.19.0.3
        ansible_user: vagrant

      hosts:
        storage-1-replica:
```

### Configuring replicasets

Now we should describe replica sets:

* `core-1` (`vshard-router`, `failover-coordinator`):
  * `core-1`

* `storage-1` (`vshard-storage`):
  * `storage-1-leader`
  * `storage-1-replica`

Since we configure **instanses** we should specify replica set parameters for
each instance.
Let's use groups again:

```yaml
all:
  vars:
    ...
  hosts:
    ...
  children:
    machine_1:
      ...
    machine_2:
      ...

    replicaset_core_1:
      hosts:
        core-1:
      vars:
        replicaset_alias: core-1
        roles:
          - vshard-router
          - failover-coordinator

    replicaset_storage_1:
      hosts:
        storage-1:
        storage-1-replica:
      vars:
        replicaset_alias: storage-1
        roles:
          - vshard-storage
        failover_priority:
          - storage-1
          - storage-1-replica
```

**Note**, that replicaset group name doesn't affect cluster configuration, but
it can be used with `--limit` option:

```bash
ansible-playbook -i hosts.yml playbook.yml \
    --limit replicaset_storage_1
```
