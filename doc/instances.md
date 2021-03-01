# Instances

Each instance of application is started as `<app_name>@<instance_name>` systemd service.
`instance_name` is `inventory_hostname` from Ansible inventory.

Instances are identified by aliases that are set equal to Ansible host names.

## Restarting instances

Instance is restarted only if it's required to apply changes
(instance configuration was changed or package was updated).
But instance restart can be forced or disabled by `restarted` flag.
If this flag isn't set, role decides if instance should be restarted.

## Expelling instances

To expel instance from topology specify `expelled: true`.
See [topology doc](/doc/topology.md#expelling-instances) for deatils

## Instance config

Instance can be configured using the [`config`](/doc/variables.md#instances-configuration) variable.
Fro specifying parameters that are common for all instances, use
[`cartridge_defaults`](/doc/variables.md#instances-configuration) varieble.
This variables describe instance parameters that would be passed to cartridge configuration.
It can contain [cluster-specific](https://www.tarantool.io/en/doc/latest/book/cartridge/cartridge_api/modules/cartridge.argparse/#cluster-opts) parameters or some application-specific parameters (can be parsed in application using the [`cartridge.argparse`](https://www.tarantool.io/en/doc/latest/book/cartridge/cartridge_api/modules/cartridge.argparse) module).

### Required parameters

`advertise_uri` is required for instance configuration.
It must be specified in `<host>:<port>` format.

### Forbidden parameters

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

### Managing dynamic `box.cfg` parameters without restart

Some `box.cfg` options are dynamic, it means that it can be changed without
instance restarting.
See [parameters](https://www.tarantool.io/en/doc/latest/reference/configuration/#configuration-parameters)
with "Dynamic: yes".

Role changes these parameters without restarting the instance.
If other parameters are changed, `needs_restart` is set to `true`.

**Note**, that if `restarted` flag is set, instance will be restarted anyway without changing dynamic parameters in runtime.
You can use this flag to force instance restarting.

#### Increasing memtx_memory in runtime

If you specified in `config.memtx_memory` value that increases current `memtx_memory`, this role will try to increase this value in runtime.
In case of success instance wouldn't be restarted (if other parameters haven't been changed).

**Note**, that if `restarted` flag is set, instance will be restarted anyway without changing `memtx_memory` in runtime.
You can use this flag to force instance restarting.
