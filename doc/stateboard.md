# Stateboard

Stateboard is a Tarantool state provider for stateful failover.
It is delivered within an application's package.
To mark an instance as a stateboard, use the `stateboard` flag.

A stateboard instance is started as a systemd service named `<app_name>-stateboard`.

## Configuring stateboard

Stateboard can be configured using the
[`config`](/doc/variables.md#instances-configuration)
variable as well as other instances.
This variable describes stateboard parameters that would be passed to its
configuration.

**Note:** [`cartridge_defaults`](/doc/variables.md#instances-configuration)
doesn't affect a stateboard instance.

### Required config parameters

* `listen` - stateboard instance URI.
  It must be specified in the `<host>:<port>` format.

* `password` - stateboard instance password.

### Forbidden config parameters

`alias`, `console_sock`, `pid_file`, and `workdir` parameters are forbidden
for a stateboard instance.

*Example*

```yaml
---
all:
  vars:
    cartridge_app_name: myapp
    cartridge_package_path: ./myapp-1.0.0-0.rpm

    # other cartridge params
    ...

    # FAILOVER PARAMS
    cartridge_failover_params:
      mode: stateful
      state_provider: stateboard
      stateboard_params:
        uri: 172.19.0.2:3310 # <- STATEBOARD URI
        password: secret-stateboard # <- STATEBOARD PASSWORD

  hosts:
    # STATEBOARD INSTANCE
    my-stateboard-instance:  # instance name doesn't matter
      stateboard: true  # this matters - instance is a stateboard
      config:
        listen: '172.19.0.2:3310' # <- STATEBOARD URI
        password: 'stateboard-secret' # <- STATEBOARD PASSWORD

    # APPLICATION INSTANCES
    core-1:
      ...
    ...
```
