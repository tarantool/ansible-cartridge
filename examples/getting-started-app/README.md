# Tarantool Cartridge Application deploy example

Here we will show you how to easily deploy your Tarantool Cartridge application, set up topology and configure cluster.

**TODO** table of contents

## Setting up the environment

**TODO**

## Create test application

We will use [`getting-started-app`](https://github.com/tarantool/cartridge-cli/tree/master/examples/getting-started-app) to show how to deploy Tarantool Cartridge application in right way.

The easiest way to get the final version of `getting-started-app` is to clone it:

```bash
$ git clone https://github.com/tarantool/cartridge-cli
$ cp -R cartridge-cli/examples/getting-started-app .
$ rm -rf cartridge-cli
```

Now we have `getting-started-app` directory containing our test app.

Let's pack this app.
First, install [Tarantool Cartridge CLI](https://github.com/tarantool/cartridge-cli):

```bash
$ tarantoolctl rocks install cartridge-cli
```

Then, just call

```bash
.rocks/bin/cartridge pack rpm --version 1.0.0 ./getting-started-app
```

Now, we have `getting-started-app-1.0.0-0.rpm` file in current directory.
The next step is to deploy this package on server and set up cluster.

**TODO** explain problems with OS X.

## Steps to deploy manually

This is a description of deploy steps, just to understand the way Tarantool Cartridge applications have to be deployed.

### Deploy package

The first step is to install application package on deploy server.
It would create user `tarantool` with group `tarantool` and some directories for our app:

* `/etc/tarantool/conf.d/` - directory for instances config (described below);
* `/var/lib/tarantool/` - directory to store instances snapshots;
* `/var/run/tarantool/` - directory to store PID-files and console sockets.

Application code would be placed in `/usr/share/tarantool/${app-name}` directory.
If you use Tarantool Enterprise, `tarantool` and `tarantoolctl` binaries would be delivered with package and placed there too.
Otherwise, you need to install Tarantool package manually.

Package also contains `/etc/systemd/system/${app-name}.service` and `/etc/systemd/system/{app-name}@.service` [systemd unit files](https://www.digitalocean.com/community/tutorials/understanding-systemd-units-and-unit-files).

### Instances start

When you call `systemctl start getting-started-app@storage-1` systemd starts `storage-1` instance of `getting-started-app` service (see [systemd template units](https://fedoramagazine.org/systemd-template-unit-files/)).
This instance would look for it's configuration across all `/etc/tarantool/conf.d/*` yaml files sections.

See [documentation](https://www.tarantool.io/en/doc/2.2/book/cartridge/cartridge_dev/#configuring-instances) for instances configuration details.

### Cluster configuration

After instances was started you need to set up cluster topology, manage auth parameters, browse application config, enable automatic failover and bootstrap vshard.
All of this actions can be performed using cluster WebUI or `cartridge` module.
To use `cartridge` Lua module you can connect to instance console using socket:

```bash
$ tarantoolctl connect /var/run/tarantool/getting-started-app.storage-1.control
tarantool> require('cartridge').is_healthy()
```

## Steps to deploy using Ansible

### Ansible

**TODO:** short description, links to manuals (hope they exist), maybe hightlight some things (like host_vars, group_vars, become, remote_user etc)

### Example topology

**TODO:** come up with an example topology (probably steal it from getting-started-app), describe it.

### Prepare to deploy

We packed our application in `getting-started-app-1.0.0-0.rpm`.

Now, we will start 4 instances on 2 different servers, join them in 2 replicasets, bootstrap vshard, enable automatic failover, set up authorization and application config.

First, use [vagrant](https://www.vagrantup.com/intro/index.html) to start two virtual machines on `172.19.0.2` and `172.19.0.3`.

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

Next, clone Tarantool Cartridge role into `tarantool-cartridge` directory.

```bash
$ git clone https://github.com/tarantool/ansible-cartridge.git tarantool-cartridge
```

Then, create [ansible playbook](https://docs.ansible.com/ansible/latest/user_guide/playbooks_intro.html) and import Tarantool Cartridge role.

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

Finally, create [inventory](https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html) file:

`hosts.yml`:

```yaml
---
all:
  hosts:
    vm1:
      ansible_host: 172.19.0.2  # First host
      ansible_user: vagrant

    vm2:
      ansible_host: 172.19.0.3  # Second host
      ansible_user: vagrant
```

Directory structure:

```
.
├── Vagrantfile
├── getting-started-app
├── getting-started-app-1.0.0-0.rpm
├── hosts.yml
├── playbook.yml
├── tarantool-cartridge
```

### Deploy itself

First, start virtual machines:

```bash
vagrant up
```

Now we will gradually upgrade our `hosts.yml` file to deploy and configure our application step-by-step.

The final version of `hosts.yml` is [here](#full-inventory).
In next steps only new sections of inventory are showed, but you always can look at the full inventory.

### Deploy package

To specify path to package to be deployed we need to add `cartridge_package_path` variable to our inventory file.

```yaml
---
all:
  ...
  vars:
    cartridge_package_path: ./getting-started-app-1.0.0-0.rpm  # Path to package to deploy
```

Now, run playbook:

```bash
$ ansible-playbook -i hosts.yml playbook.yml
```

Then, connect to the `vm1` and check if package was installed:

```bash
$ vagrant ssh vm1
[vagrant@vm1 ~]$ yum list installed | grep getting-started-app
getting-started-app.x86_64          1.0.0-0                     installed
[vagrant@vm1 ~]$ exit
```

You can check that application files were placed in `/usr/share/tarantool/getting-started-app/`.

The same for `vm2`.

Note, that if you used opensource Tarantool, your package has Tarantool dependency.
Tarantool Cartridge role would enable Tarantool package repo to let Tarantool to be automatically installed with your application.
If you want to install Tarantool by yourself (e.g. from package), you can set `cartridge_enable_tarantool_repo` variable to `false`.

### Instances

Next, configure and start instances.

Add `cartridge_instances`, `cartridge_cluster_cookie` and `cartridge_defaults` sections:

```yaml
---
all:
  hosts:
    vm1:
      ...
      cartridge_instances:  # instances to be started on this host
        - name: 'storage-1'
          advertise_uri: '172.19.0.2:3301'
          http_port: '8181'

    vm2:
      ...
      cartridge_instances:  # instances to be started on this host
        - name: 'app-1'
          advertise_uri: '172.19.0.3:3301'
          http_port: '8181'

        - name: 'storage-1-replica'
          advertise_uri: '172.19.0.3:3302'
          http_port: '8182'

  vars:
    cartridge_app_name: getting-started-app  # application name

    cartridge_cluster_cookie: app-default-cookie  # cluster cookie
    cartridge_defaults:  # default instances parameters
      log_level: 5
```

Note, that we use `cartridge_app_name` (we don't deploy new package) instead of `cartridge_package_path`.
You can use both options, but it's required to specify at least one of them.
If `cartridge_app_name` isn't set, it would be discovered from package info.

Connect to machines and check if all instances was started:

```bash
$ vagrant ssh vm1
[vagrant@vm1 ~]$ sudo systemctl status getting-started-app@storage-1
[vagrant@vm1 ~]$ exit
$ vagrant ssh vm2
[vagrant@vm2 ~]$ sudo systemctl status getting-started-app@app-1
[vagrant@vm2 ~]$ sudo systemctl status getting-started-app@storage-1-replica
[vagrant@vm2 ~]$ exit
```

All instances must be `active (running)`.

Instance log:

```bash
$ vagrant ssh vm1
[vagrant@vm1 ~]$ sudo journalctl -u getting-started-app@storage-1
```

You can check instances configuration files in `/etc/tarantool/conf.d/`:

```bash
$ vagrant ssh vm1
[vagrant@vm1 ~]$ sudo ls /etc/tarantool/conf.d/
getting-started-app.storage-1.yml  getting-started-app.yml
[vagrant@vm1 ~]$ sudo cat /etc/tarantool/conf.d/*
getting-started-app.storage-1:
    advertise_uri: 172.19.0.2:3301
    http_port: '8181'
getting-started-app:
    cluster_cookie: app-default-cookie
    log_level: 5
```

You can also check `/var/run/tarantool/` and `/var/lib/tarantool/` content.

Go to http://localhost:8181/admin/cluster/dashboard to see our instances in Web UI:

![Unconfigured instances](./images/unconfiured-instances.png)

If you change instance configuration in `cartridge_instances` and run playbook, this instance configuration file in `/etc/tarantool/conf.d/` would be changed and systemd service would be restarted.
You can experiment with adding new instances and changing   `cartridge_instances`, `cartridge_cluster_cookie` and `cartridge_defaults` sections.
Note, that playbook would affect only instances mentioned in config.
Instances expelling is described in [TODO] section.

### Replicasets

TODO: merge edit-topology and rewrite this section

Now we have instances running on two hosts.
It's time to join them to replicaset.
Describe them in `cartridge_replicasets` variable:

```yaml
---
all:
  hosts:
    ...

  vars:
    ...
    cartridge_replicasets:  # replicasets to be set up
      - name: 'app-1'
        instances:
          - 'app-1'
        roles: ['api']

      - name: 'storage-1'
        instances:
          - 'storage-1'
          - 'storage-1-replica'
        leader: 'storage-1'
        roles: ['storage']
```

Run playbook and then go to http://localhost:8181/admin/cluster/dashboard.

![Replicasets](./images/replicasets.png)

Note, that `storage-1` replicaset has two roles: `storage` and it's dependency `vshard-storage`, `app-1` has roles: `api` and `vshard-router`.

### Vshard

Now, when we have both `vshard-storage` and `vshard-router` replicasets, we can bootstrap vshard.
Just set `cartridge_bootstrap_vshard` flag and run the playbook again.

TODO: when edit-topology would be merged, explain how to edit replicasets.

```yaml
---
all:
  ...
  vars:
    ...
    cartridge_bootstrap_vshard: true  # bootstrap vshard
    ...
```

Now you can check that `Bootstrap vshard` button disappeared from the Web UI and `storage-1` replicaset `Buckets` value has been changed.

### Failover

If you want to manage automatic failover, use `cartridge_failover` variable:

```yaml
---
all:
  ...
  vars:
    ...
    cartridge_failover: true  # enable failover
    ...
```

Run the playbook and check failover switcher in Web UI.
You can experiment with `cartridge_failover` value.
If this value isn't set, failover status wouldn't be affected.

### Auth

Our app is already configured and run, but what about security?

Let's create a new user, set up auth parameters and enable Cartridge auth:

```yaml
---
all:
  ...
  vars:
    ...
    cartridge_auth:
        enabled: true

        cookie_max_age: 1000
        cookie_renew_age: 100

        users:
          - username: first-user
            password: first-user-password
            fullname: First Cartridge User
            email: user@cartridge.org
    ...
```

After running playbook go to http://localhost:8181/admin/cluster/dashboard and you will see the authorization form. 
Default user is `admin`, it's password is `cartridge_cluster_cookie` value.
You can log in using new user credentials.
Then, go to the `Users` tab and check if user was added.

To delete user just set `deleted` flag for it:

```yaml
---
all:
  ...
  vars:
    ...
    cartridge_auth:
        ...
        users:
          - username: first-user
            password: first-user-password
            fullname: First Cartridge User
            email: user@cartridge.org
            deleted: true
    ...
```

You can change authorization parameters and users configuration.
Note, that only mentioned users would be affected.

### Application config

You can configure your roles using [cluster-wide configuration](https://www.tarantool.io/en/doc/2.2/book/cartridge/cartridge_dev/#configuring-custom-roles).
To download current config go to the `Configuration files` tab in Web UI.
You can patch clusterwide config sections using Ansible.

```yaml
---
all:
  ...
  vars:
    ...
    cartridge_app_config:
      customers:
        body:
          max-age: 100
          max-accounts-num: 5

      accounts:
        body:
          max-balance: 10000000
    ...
```
Run playbook and check config again - it would contain new sections.

To delete section you have to set `deleted` flag:

```yaml
---
all:
  ...
  vars:
    ...
    cartridge_app_config:
      customers:
        body:
          max-customer-age: 100
          max-customer-accounts-num: 5
        deleted: true  # delete section from config
    ...
```

Note, that only mentioned sections would be affected.

### Instances expelling

**TODO** first merge edit-topology

(find the Cartridge doc for all this things)

### Full inventory

```yaml
---
all:
  hosts:
    vm1:
      ansible_host: 172.19.0.2  # first host
      ansible_user: vagrant

      cartridge_instances:  # instances to be started on this host
        - name: 'storage-1'
          advertise_uri: '172.19.0.2:3301'
          http_port: '8181'

    vm2:
      ansible_host: 172.19.0.3  # second host
      ansible_user: vagrant

      cartridge_instances:  # instances to be started on this host
        - name: 'app-1'
          advertise_uri: '172.19.0.3:3301'
          http_port: '8181'

        - name: 'storage-1-replica'
          advertise_uri: '172.19.0.3:3302'
          http_port: '8182'

  vars:
    cartridge_package_path: ./getting-started-app-1.0.0-0.rpm  # path to package to deploy
    # cartridge_app_name: getting-started-app  # can be used if package is already installed

    cartridge_cluster_cookie: app-default-cookie  # cluster cookie
    cartridge_defaults:  # default instance parameters
      log_level: 5

    cartridge_bootstrap_vshard: true  # bootstrap vshard

    cartridge_auth:
      enabled: true

      cookie_max_age: 1000
      cookie_renew_age: 100

      users:
        - username: first-user
          password: first-user-password
          fullname: First Cartridge User
          email: user@cartridge.org
          # deleted: true  # delete user

    cartridge_replicasets:  # replicasets to be set up
      - name: 'app-1'
        instances:
          - 'app-1'
        roles: ['api']

      - name: 'storage-1'
        instances:
          - 'storage-1'
          - 'storage-1-replica'
        leader: 'storage-1'
        roles: ['storage']

    cartridge_app_config:
      customers:
        body:
          max-age: 100
          max-accounts-num: 5

      accounts:
        body:
          max-balance: 10000000
        # deleted: true  # delete section from config
```
