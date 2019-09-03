# Ansible Cartridge

Ansible scripts to easy deploy Tarantool Cartridge applications.

## When should you use it?

You can use this scripts to deploy application created using [Tarantool Cartridge](https://github.com/tarantool/cartridge) framework and its [CLI](https://github.com/tarantool/cartridge-cli).

## How to deploy?

This repo contains example RPM and configuration for ansible.

#### RPM

Example RPM placed in `rpms/` folder.

It was created using [Cartridge CLI](https://github.com/tarantool/cartridge-cli):

```bash
tarantoolctl rocks install cartridge-cli
.rocks/bin/cartridge create --name myapp .
.rocks/bin/cartridge pack rpm myapp
```

#### Configuration

In example next configuration is deployed:

```yaml
default:
  cluster_cookie: app-default-cookie
  
vm1:
  default:
    cluster_cookie: this-server-default-cookie

  instances:
    - name: 'core_1'
      advertise_uri: '3000'
      http_port: '8080'

    - name: 'storage_1'
      advertise_uri: '3002'
      http_port: '8082'

vm2:
  instances:
  - name: 'core_2'
    advertise_uri: '3004'
    http_port: '8084'

  - name: 'storage_1_replica'
    advertise_uri: '3005'
    http_port: '8085'
```

Configuration is passed to Ansible using var files placed in `group_vars/` and `host_vars/` dirs.

In `group_vars/all.yml` we need to declare app name and version to deploy (Ansible will find `myapp-0.1.0-0.rpm` file in `rpms/` folder):

```yaml
app: myapp
version: 0.1.0-0
```

In `host_vars/` directory are placed server configs:

* `cluster_config` table declares cluster configuration for server.

* `cluster_config_default` table declares application- or server-specific cluster config default values.

#### Deploy example

First, you need [Vagrant](https://www.vagrantup.com/). Then, if you'll be running with VirtualBox, [install it as well](https://www.virtualbox.org/wiki/Downloads).

To start 2 centos:7 VMs just run this in the project root:

```bash
vagrant up
```

This will bring up 2 virtual machines. IP addresses of those machines: 172.19.0.2 and 172.19.0.3.

This machines are described in `hosts.yml` file of project root.

To deploy example RPM with example configuration on this VMs run (in project root):

```bash
ansible-playbook -i hosts.yml site.yml
```

Then, you can ssh to vm1 and check if services was started correctly:

```bash
vagrant ssh vm1
> systemctsl status myapp@core_1
> systemctl status myapp@storage_1
```

You can also check Cartridge config files that was placed in `/etc/tarantool/conf.d` folder.

## Molecule

To run molecule tests for `deploy` role (in `roles/deploy/` folder):

```bash
molecule test
```

Molecule test configuration (the same as example configuration) is described in `provisioner.inventory` section of `roles/deploy/molecule/default/molecule.yml` file.
VMs are described in `platforms` section of this file.

To deploy configuration using molecule:

```bash
molecule converge
```

After, you can check if it's OK:

```bash
molecule login --host vm1
> systemctsl status myapp@core_1
> systemctl status myapp@storage_1
```

Don't forget to destroy VMs:

```bash
molecule destroy
```
