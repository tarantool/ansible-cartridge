# Ansible Role: Cartridge

An Ansible Role to easy deploy [Tarantool Cartridge](https://github.com/tarantool/cartridge-cli) applications.

This role can deploy applications packed in RPM using [`Cartridge CLI`](https://github.com/tarantool/cartridge-cli).

If application instances are [configured](#instances-configuration), this role would start systemd services for this instances.

If cluster replicasets are [configured](#replicasets-configuration), replicasets will be set up according to configuration.

**Note:** Topology management is not supported yet, so this role can be used for initial deployment and package updating.

## Requirements

None.

## Role Variables

Role variables are used to configure started instances, cluster topology, vhsard bootstrapping and failover.

Configuration format is described in detail in [configuration format](#configuration-format) section.

* `cartridge_package_path` (`string`, required): path to cartridge RPM package (application name will be detected as package name);
* `cartridge_instances` (`list`, optional, default: `[]`): configuration for deployed instances;
* `cartridge_defaults` (`dict`, optional, default: `{}`): default configuration instances;
* `cartridge_replicasets` (`list`, optional, default: `[]`) - replicasets configuration;
* `cartridge_bootstrap_vshard` (`boolean`, optional, default: `false`): boolean flag indicates if vshard must be bootstrapped;
* `cartridge_failover` (`boolean`, optional, default: `false`): boolean flag indicates if failover must be enabled.

## Configuration format

Instances and replicasets are identified by names, so you must use unique names to aviod collisions.

### Instances configuration

Each instance of application is started as `<app_name>@<instance_name>` systemd service.

It can be configured using `cartridge_instances` variable. 
This variable describes all instances that should be deployed on host.

`cartridge_instances` is a list of dicts, each dict must have field `name`.
Other parameters can specify [cluster-specific](https://www.tarantool.io/en/rocks/cartridge/1.0/modules/cartridge.argparse/#cluster-opts) parameters or some application-specific parameters (can be parsed in application using [`cartridge.argparse`](https://www.tarantool.io/en/rocks/cartridge/1.0/modules/cartridge.argparse) module).

**Note:** It's recommended to specify both host and port for `advertise_uri` parameter.
If your deploy host has more than one non-local IP address, advertise host will be set to `localhost`.

*Example:*
```yaml
cartridge_instances:
  - name: 'core_1'
    advertise_uri: '172.19.0.2:3301'
    http_port: '8081'

  - name: 'storage_1'
    advertise_uri: '172.19.0.2:3302'
    http_port: '8082'
```

Some parameters can be same for all instances (e.g. `cluster_cookie`).
You can specify such parameters using `cartridge_defaults` variable.

*Example:*
```yaml
cartridge_defaults:
  cluster_cookie: super-secret-cookie
```

**Note:** All configured instances would be started on host **only** if instances with the same names are not started on this host.

### Replicasets configuration

Cluster topology can be configured using `cartridge_replicasets` variable (must be placed in `all` group).

`cartridge_replicasets` is a list of `replicaset` dicts:

* `replicaset.name` (`string`, required) - name of replicaset, will be displayed in Web UI;
* `replicaset.instances` (`list-of-strings`, required) - names of instances, which must be joined to replicaset;
* `leader` (`string`) - name of leader instance. Optional if replicaset contains only one instance, required for replicaset with more than one instances;
* `roles` (`list-of-strings`, required) - roles to be enabled on the replicaset.

*Example:*
```yaml
cartridge_replicasets:
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
```

### Bootstrap vshard

Flag `cartridge_bootstrap_vshard` indicates if vshard must be bootstrapped on cluster.

First, it would be checked if it is reasonble to bootstrap VShard (cluster must have at least one `vshard-storage` replicaset and at least one `vshard-router`).
If it is, VShard will be bootstrapped.

### Failover

If `cartridge_bootstrap_vshard` is `true`, then failover will be enabled.
