# Ansible Role: Cartridge

An Ansible Role to easy deploy [Tarantool Cartridge](https://github.com/tarantool/cartridge-cli) applications.

## Requirements

* [computology.packagecloud](https://galaxy.ansible.com/computology/packagecloud)

## Role Variables

* `cartridge_package_path` (required): path to cartridge package (application name will be detected as package name);
* `cartridge_config` (optional, default: `{}`): configuration for deployed application (see [below](#configuration-format));
* `cartridge_config_defaults` (optional, default: `{}`): default configuration for deployed application instances (see [below](#configuration-format)).

## Configuration format

Deployed application configuration (`cartridge_config`) describes parameters for instances that should be started on host. 
Instances configurations are placed in `instances` subsection.
Instance config must contain `name` field to be used for systemd service instance name.
Other parameters can be cluster-specific or application-specific (see [Cartridge Argparse doc](https://github.com/tarantool/cartridge/blob/master/cartridge/argparse.lua#L12-L35)) .

For each instance will be created configuration file in `/etc/tarantool/conf.d/` directory. 

**Example**:

Let app name be `myapp`.
For this `cartridge_config` variable

```yaml
cartridge_config:
  instances:
    - name: 'core_1'
      advertise_uri: '3000'
      http_port: '8080'

    - name: 'storage_1'
      advertise_uri: '3002'
      http_port: '8082'
```

for `core_1` instance will be created file `/etc/tarantool/conf.d/myapp.core_1.yml`:

```yaml
myapp.core_1:
  advertise_uri: '3000'
  http_port: '8080'
```

### Default values

`cartridge_config_defaults` can contain some default values that must be used for all application instances (if this patameters are not specified for instance).

If default application values are specified then would be created default application config file in `/etc/tarantool/conf.d/`.

**Example**:

Let app name be `myapp`.
For this `cartridge_config_defaults` variable

```yaml
cartridge_config:
  cluster-cookie: very-big-secret
```

for this application will be created file `/etc/tarantool/conf.d/myapp.yml`:

```yaml
myapp:
  cluster-cookie: very-big-secret
```
