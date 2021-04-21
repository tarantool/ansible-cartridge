# Rolling update

Here is described rolling update for an application that uses
TGZ package with [multiversion approach](/doc/multiversion.md) or
usual RPM/DEB packages.

## Requirements

* `tarantool.cartridge` >= `1.9.0`

## Leaders promotion

[`failover_promote`](/doc/scenario.md#failover_promote) and
[`force_leaders`](/doc/scenario.md#force_leaders)
steps can be used for leaders promotion only if stateful failover is enabled.

The main difference of these steps is:

* `failover_promote` - promotes leaders according to specified parameters;
* `force_leaders` - promotes leaders to current play hosts (instances specified
  in limit); can be useful to switch leaders to specified data center.

### Using `failover_promote` step

To specify leaders that should be promoted `cartridge_failover_promote_params` variable
should be used. It's a dictionary with fields:

* `replicaset_leaders` (`dict`): describes the mapping between replica sets
and leaders aliases;
* `force_inconsistency` (`bool`): make promotion forcefully, don't wait for the
consistent switchover.

This playbook says: **Promote leaders directly to these instances**:

```yml
- name: Promote storages leaders to replicas
  hosts: all
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario:
      - failover_promote
    cartridge_failover_promote_params:
      force_inconsistency: true
      replicasets_leaders:
        storage-1: storage-1-replica
        storage-2: storage-2-replica
```

### Using `force_leaders` step

To specify leaders that should be promoted Ansible limit is used.
`cartridge_failover_promote_params` variable can be used to specify other
parameters:

* `force_inconsistency` (`bool`): make promotion forcefully, don't wait for the
consistent switchover.

For example, you want to switch all leaders to data center 1.
You have group `DC1` in your inventory that describes which instances belong to
this data center.

Just specify this group in `hosts` parameters of the play or use `--limit` option
on playbook running.

Leaders are chosen by these rules:

* each play host that doesn't belong to replicaset is ignored;
* all instances that has status other than `alive` are ignored;
* if play hosts contain two instances from one replicaset, then one with higher
  failover priority is chosen;
* if all instances on one replicaset present in play hosts aren't alive, promotion
  is performed for the rest instances, but task fails with critical warnings;

This playbook says: **Promote leaders to instances from "DC1" group**:

```yml
- name: Promote storages leaders instances from DC1
  hosts: DC1
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario:
      - failover_promote
    # can be additionally specified:
    cartridge_failover_promote_params:
      force_inconsistency: true
```

## Rolling update: Plan

Imagine that you have a cluster with `myapp-1.0.0` deployed.
Now you want to update your application to `myapp-2.0.0`.

The plan is quite simple:

* deliver and install a new package on machines
* update stateboard instance
* update replicas instances of storages replica sets
* promote storages leaders to current replicas
* update leaders instances of storages replica sets
* promote storages leaders back
* update routers replica sets
* rotate distributions (if TGZ + Multiversion is used)

## Rolling update: Playbook for TGZ package + Multiversion

[Multiversion approach](/doc/multiversion.md) allows updating application
version that each instance uses with
[`update_instance` step](/doc/scenario.md#update_instance).

Additionally, there is [`rotate_dists` step](/doc/scenario.md#rotate_dists) that
removes redundant distributions.

Updating and restarting instance scenario can be persisted in inventory
to be used by name in all plays:

```yaml
# hosts.yml

all:
  vars:
    ...
    cartridge_custom_scenarios:
      update_and_restart_instance:
        - update_instance
        - restart_instance
        - wait_instance_started
    ...
```

**Note** that [`update_instance` step](/doc/scenario.md#update_instance) requires
`cartridge_package_path` variable to set instance application link to unpacked
distribution.

The example rolling update playbook:

```yaml
# playbook.yml

- name: Deliver and install myapp 2.0.0
  hosts: all
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario:
      - deliver_package
      - update_package
    cartridge_package_path: ./myapp-2.0.0.tar.gz

- name: Update stateboard application version
  hosts: "my-stateboard"
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario_name: update_and_restart_instance
    cartridge_package_path: ./myapp-2.0.0.tar.gz

- name: Update storages replicas application version
  hosts: "*storage*replica*"
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario_name: update_and_restart_instance
    cartridge_package_path: ./myapp-2.0.0.tar.gz

- name: Promote storages leaders to replicas
  hosts: all
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario:
      - failover_promote
    cartridge_failover_promote_params:
      replicasets_leaders:
        storage-1: storage-1-replica
        storage-2: storage-2-replica

- name: Update storages leaders application version
  hosts: "*storage*leader*"
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario_name: update_and_restart_instance
    cartridge_package_path: ./myapp-2.0.0.tar.gz

- name: Promote storages leaders back
  hosts: all
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario:
      - failover_promote
    cartridge_failover_promote_params:
      replicasets_leaders:
        storage-1: storage-1-leader
        storage-2: storage-2-leader

- name: Update routers application version
  hosts: "*core*"
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario_name: update_and_restart_instance
    cartridge_package_path: ./myapp-2.0.0.tar.gz

- name: Remove old packages
  hosts: all
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario:
      - rotate_dists
    cartridge_keep_num_latest_dists: 1
```

## Rolling update: Playbook for RPM or DEB packages

In case of RPM and DEB (or TGZ without [multiversion approach](/doc/multiversion.md))
all instances use a common version of the application.
Updating the instance version of the application is performed when the instance is restarted.

Updating instance scenario can be persisted in inventory to be used by name in all plays:

```yaml
# hosts.yml

all:
  vars:
    ...
    cartridge_custom_scenarios:
      restart_instance_to_update:
        - restart_instance
        - wait_instance_started
    ...
```

The example rolling update playbook:

```yaml
# playbook.yml

- name: Deliver and install myapp 2.0.0
  hosts: all
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario:
      - deliver_package
      - update_package
    cartridge_package_path: ./myapp-2.0.0.rpm

- name: Update stateboard application version
  hosts: "my-stateboard"
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario_name: restart_instance_to_update

- name: Update storages replicas application version
  hosts: "*storage*replica*"
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario_name: restart_instance_to_update

- name: Promote storages leaders to replicas
  hosts: all
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario:
      - failover_promote
    cartridge_failover_promote_params:
      replicasets_leaders:
        storage-1: storage-1-replica
        storage-2: storage-2-replica

- name: Update storages leaders application version
  hosts: "*storage*leader*"
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario_name: restart_instance_to_update

- name: Promote storages leaders back
  hosts: all
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario:
      - failover_promote
    cartridge_failover_promote_params:
      replicasets_leaders:
        storage-1: storage-1-leader
        storage-2: storage-2-leader

- name: Update routers application version
  hosts: "*core*"
  roles:
    - tarantool.cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario_name: restart_instance_to_update
```
