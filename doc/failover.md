# Configuring failover


[`cartridge_failover_params`](/doc/variables.md#cluster-configuration)
is used to specify failover parameters:

- `mode`(`string`, required) - failover mode. Possible values are `disabled`,
  `eventual` and `stateful`.

Other parameters are mode-specific.

Read [the doc](https://www.tarantool.io/en/doc/latest/book/cartridge/cartridge_api/topics/failover.md/)
to learn more about Cartridge failover.

#### Eventual

If `eventual` mode is specified, there are no additional parameters.

Read [the doc](https://www.tarantool.io/en/doc/latest/book/cartridge/cartridge_api/topics/failover.md/#eventual-failover)
to learn more about eventual failover.

*Example:*

```yaml
cartridge_failover_params:
  mode: eventual
```

#### Stateful

**Note** that stateful failover is supported since `Cartridge` 2.1.2.

**Note** that `etcd2` provider is supported since `Cartridge` 2.2.0.

`stateful` failover requires these parameters:

- `state_provider`(`string`, required for `stateful` mode) - external state
  provider type. Supported `stateboard` and `etcd2` providers.

- `stateboard_params`(`dict`, required for `stateboard` state provider) -
  configuration for stateboard:
    - `uri`(`string`, required) - stateboard instance URI;

    - `password`(`string`, required) - stateboard instance password;

- `etcd2_params`(`dict`, used for `etcd2` state provider) -
  configuration for stateboard:
    - `prefix`(`string`) - prefix used for etcd keys: `<prefix>/lock` and
      `<prefix>/leaders`;

    - `lock_delay`(`number`) - timeout (in seconds), determines lock's
      time-to-live (default value in Cartridge is `10`);

    - `endpoints`(`list-of-strings`) - URIs that are used to discover and to access
      `etcd` cluster instances (default value in Cartridge is
      `['http://localhost:2379', 'http://localhost:4001']`);

    - `username`(`string`).

    - `password`(`string`).

Read [the doc](https://www.tarantool.io/en/doc/latest/book/cartridge/cartridge_api/topics/failover.md/#stateful-failover)
to learn more about stateful failover.

*Example:*

```yaml
cartridge_failover_params:
  mode: stateful
  state_provider: stateboard
  stateboard_params:
    uri: localhost:3310
    password: stateboard-secret

```
