# Replicasets

You can find more details about replicasets and automatic failover in [Tarantool Cartridge administrator’s guide](https://www.tarantool.io/en/doc/latest/book/cartridge/cartridge_admin/#enabling-automatic-failover).

## Replicasets configuration

To configure replicasets you need to specify
[replicaset parameters](/doc/variables.md#replicasets-configuration)
for each instance in replicaset.

The easiest way to configure replicaset is to [group instances](https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html) and set replicaset parameters for all instances in a group.

```yaml
all:
  vars:
    cartridge_app_name: myapp
    ...

  hosts:  # instances
    storage-1:
      config:
        advertise_uri: '172.19.0.3:3301'
        http_port: 8091

    storage-1-replica:
      config:
        advertise_uri: '172.19.0.2:3302'
        http_port: 8082

  children:
    # group instances by machines
    ...

    # group instances by replicasets
    storage_1_replicaset:  # replicaset storage-1
      hosts:  # instances
        storage-1:
        storage-1-replica:
      vars:
        # replicaset configuration
        replicaset_alias: storage-1
        weight: 2
        failover_priority:
          - storage-1  # leader
          - storage-1-replica

        roles:
          - 'vshard-storage'
```

### Specifying vshard group

If your application is designed to use multiple independent vshard groups (see cartridge
[documentation](https://www.tarantool.io/en/doc/latest/book/cartridge/cartridge_dev/#using-multiple-vshard-storage-groups)), you can specify vshard group for `vshard-storage` replicaset `vshard_group`
parameter.
This parameter will be ignored for replicaset with other roles.
By default, all `vshard-storage` replicasets belong to group `default`

Be very careful using this parameter.
Once you specified `vshard_group`, it can't be changed.
Moreover, **your application should support specified group**.
It means that your  application should pass vshard groups configuration in
`cartridge.cfg()` call.

For example, if your application configures `hot` and `cold` vshard groups ...

```lua
-- init.lua

...
cartridge.cfg({
  ...
  vshard_groups = {
    hot = { bucket_count = 20000 },
    cold = { bucket_count = 30000 },
  }
})
```

... you can specify them to be used by `vshard-storage` replicaset:

```yaml
    hot_storage_replicaset:
      hosts:
        hot-storage:
      vars:
        replicaset_alias: hot-storage
        roles: [vshard-storage]
        vshard_group: hot
```

## Expelling instances

To expel instance set `expelled` flag to true.
For example:

```yaml
  core-1:
    config:
      advertise_uri: '172.19.0.2:3301'
      http_port: 8081
    expelled: true  # mark instance to be expelled
```

Instances expelling is performed on `edit_topology` step.

After expelling instance from the topology, it's systemd service would be stopped
and disabled.

After that, all instance files
(configuration file, socket and working directory)
are removed on [`cleanup_expelled`](/doc/scenario.md#cleanup_expelled) step.

## Advertise URIs changing

It is possible to change the advertise URIs of the servers. However, this should be done carefully.
You can read about manually changing the URIs in the [troubleshooting doc](
https://tarantool.io/en/doc/latest/book/cartridge/troubleshooting/#i-want-to-run-an-instance-with-a-new-advertise-uri).

The main problem that arises when changing URIs: after restart, the instance tries
to connect to all its replicas and remains in the `ConnectingFullmesh` state until it succeeds.
If it can’t (due to replica URI unavailability or for any other reason) – it’s stuck forever.

To solve the problem, you should set the `replication_connect_quorum` option to zero.
To do it, you should add the option to `cartridge_defaults` or to `config` section of instances
from the replicasets that include instances with new URIs.

So, after changing advertise URIs and `replication_connect_quorum` options in configuration files,
you should run `configure_instance` and `restart_instance` steps to apply changes
(`replication_connect_quorum` can be changed without restarting,
but to change advertise URI you should restart instance).

After changing replication connect quorum and advertise URIs,
you can run `edit_topology` step to change URIs in cluster-wide config.

Now you can reset replication connect quorum to default value.

For example, you can create a playbook like this to change the URI:

```yaml
- name: Set quorum to zero
  hosts: cluster
  become: true
  gather_facts: no
  vars:
    cartridge_scenario:
      - configure_instance
      - restart_instance
      - wait_instance_started
    cartridge_defaults:
      # don't forget to add other options from your cartridge_defaults variable
      replication_connect_quorum: 0
  roles:
    - tarantool.cartridge

- name: Update advertise URIs in cluster-wide config
  hosts: cluster
  become: true
  gather_facts: no
  vars:
    cartridge_scenario:
      - edit_topology
  roles:
    - tarantool.cartridge

- name: Reset quorum to default value
  hosts: cluster
  become: true
  gather_facts: no
  vars:
    cartridge_scenario:
      - configure_instance
  roles:
    - tarantool.cartridge
```
