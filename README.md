# Ansible Role: Tarantool Cartridge

An Ansible Role to easy deploy [Tarantool Cartridge](https://github.com/tarantool/cartridge) applications.

This role can deploy applications packed in RPM using [`Cartridge CLI`](https://github.com/tarantool/cartridge-cli).

## Table of contents

* [Requirements](#requirements)
* [Getting started](#getting-started)
* [Role variables](#role-variables)
* [Configuration format](#configuration-format)
  * [Instances configuration](#instances-configuration)
  * [Replicasets configuration](#replicasets-configuration)
  * [Vshard bootstrapping](#vshard-bootstrapping)
  * [Failover](#failover)

## Requirements

None.

## Getting started

After you have learn how to [create](https://github.com/tarantool/cartridge-cli/tree/master/examples/getting-started-app) Tarantool Cartridge applications and [pack them to RPM](https://github.com/tarantool/cartridge-cli), you probably want to deploy your new application on server.

### Target configuration

For example, you packed your application to `myapp-1.0.0-0.rpm`.

Now, you want to start 4 instances on 2 different servers, join them to 2 replicasets, bootstrap vshard and enable automatic failover.

You can use [vagrant](https://www.vagrantup.com/intro/index.html) to start two virtual machines on `172.19.0.2` and `172.19.0.3`.

`Vagrantfile`:

```
$ssh_pub_key = File.readlines("#{Dir.home}/.ssh/id_rsa.pub").first.strip

$script = <<-SCRIPT
set -e
sudo bash -c "echo #{$ssh_pub_key} >> /home/vagrant/.ssh/authorized_keys"
SCRIPT

Vagrant.configure("2") do |config|
  config.vm.provider "virtualbox" do |v|
    v.memory = 2048
  end

  config.vm.define "vm1" do |cfg|
    cfg.vm.box = "centos/7"
    cfg.vm.network "private_network", ip: "172.19.0.2"
    cfg.vm.network "forwarded_port", guest: 8181, host: 8181
    cfg.vm.hostname = 'vm1'
  end

  config.vm.define "vm2" do |cfg|
    cfg.vm.box = "centos/7"
    cfg.vm.network "private_network", ip: "172.19.0.3"
    cfg.vm.hostname = 'vm2'
  end

  config.vm.provision :shell, inline: $script
end
```

First, you need to clone Tarantool Cartridge role into `tarantool-cartridge` directory.

```bash
$ git clone https://github.com/tarantool/ansible-cartridge.git tarantool-cartridge
```

Next, create [ansible playbook](https://docs.ansible.com/ansible/latest/user_guide/playbooks_intro.html) and import Tarantool Cartridge role.

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

Then, you need to create [inventory](https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html) file.

`hosts.yml`:

```yaml
---
all:
  hosts:
    vm1:
      ansible_host: 172.19.0.2  # First host
      ansible_user: vagrant

      cartridge_instances:  # Instances to be started on this host
        - name: 'core_1'
          advertise_uri: '172.19.0.2:3301'
          http_port: '8181'

        - name: 'storage_1'
          advertise_uri: '172.19.0.2:3302'
          http_port: '8182'

    vm2:
      ansible_host: 172.19.0.3  # Second host
      ansible_user: vagrant

      cartridge_instances:  # Instances to be started on this host
        - name: 'router'
          advertise_uri: '172.19.0.3:3303'
          http_port: '8183'

        - name: 'storage_1_replica'
          advertise_uri: '172.19.0.3:3304'
          http_port: '8184'


  vars:  # Cluster configuration
    cartridge_package_path: ./myapp-1.0.0-0.rpm  # Path to package to deploy

    cartridge_failover: true  # Enable automatic failover
    cartridge_bootstrap_vshard: true  # Bootstrap vshard

    cartridge_defaults:  # Default configuration parameters for all instances
      cluster_cookie: app-default-cookie

    cartridge_replicasets:  # Replicasets to be set up
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

      - name: 'router-1'
        instances:
          - router
        roles: ['vshard-router']
```

Directory structure:

```
.
├── Vagrantfile
├── hosts.yml
├── myapp-1.0.0-0.rpm
├── playbook.yml
├── tarantool-cartridge
```

Now, you need to up your virtual machines and run the playbook:

```bash
$ vagrant up
$ ansible-playbook -i hosts.yml playbook.yml
```

Then, go to http://localhost:8181/admin/cluster/dashboard and check if your topology was set up:

![image](https://user-images.githubusercontent.com/32142520/65237544-837dc580-dae3-11e9-97c6-db8676357eb5.png)

## Role variables

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

### Vshard bootstrapping

Flag `cartridge_bootstrap_vshard` indicates if vshard must be bootstrapped on cluster.

First, it would be checked if it is reasonble to bootstrap VShard (cluster must have at least one `vshard-storage` replicaset and at least one `vshard-router`).
If it is, VShard will be bootstrapped.

### Failover

If `cartridge_bootstrap_vshard` is `true`, then failover will be enabled.
