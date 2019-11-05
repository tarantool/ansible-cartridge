# Tarantool Cartridge Application deploy example

Here we will show you how to easily deploy your Tarantool Cartridge application, set up topology and configure cluster.

## Table of contents

* [What we will do?](#what-we-will-do)
* [Setting up the environment](#setting-up-the-environment)
* [Hints](#hints)
* [Pack test application](#pack-test-application)
* [Pack test application on OS X](#pack-test-application-on-os-x)
* [What does Tarantool Cartridge role do?](#what-does-tarantool-cartridge-role-do)
* [Steps to deploy using Ansible](#steps-to-deploy-using-ansible)
  * [Ansible](#ansible)
  * [Example topology](#example-topology)
  * [Prepare to deploy](#prepare-to-deploy)
  * [Start virtual machines](#start-virtual-machines)
  * [Install package](#install-package)
  * [Start instances](#start-instances)
  * [Set up replicasets](#set-up-replicasets)
  * [Bootstrap Vshard](#bootstrap-vshard)
  * [Manage failover](#manage-failover)
  * [Manage auth](#manage-auth)
  * [Application config](#application-config)
* [Final checks](#final-checks)
* [Afterword](#afterword)
* [Full inventory](#full-inventory)

## What we will do?

We have [getting started guide](https://github.com/tarantool/cartridge-cli/tree/master/examples/getting-started-app) for developing Tarantool Cartridge applications.
Now we will learn how to deploy this application on servers and set up topology using Ansible.

Example application implements two roles: `api` (with `vshard-router` dependency) and `storage` (with `vshard-router` dependency).
We will set up simple topology on 2 virtual machines: `vm1` and `vm2`:

* replicaset `app-1`:
  * roles: `api` (+ `vshard-router`)
  * instances:
    * `app-1` (`vm2`)

* replicaset `storage-1`
  * roles: `storage` (+ `vshard-storage`)
  * instances:
    * `storage-1` (`vm1`)
    * `storage-1-replica` (`vm2`)

In cluster Web UI it will look like this:

![Topology](./images/topology.png)

## Setting up the environment

To work with Tarantool Cartridge you need to install this tools:

* `git` - version control system (see details [here](https://git-scm.com/));
* `npm`- package manager for `node.js` (see details [here](https://www.npmjs.com/));
* `cmake` version 2.8 or higher;
* `tarantool`;
* `tarantool-devel` - developer package for `tarantool`;
* `gcc` - `C` compiler (see details [here](https://gcc.gnu.org/));
* `unzip`.

Note, that minimal Tarantool Cartridge version for using this role is `1.2.0`.

To run this guide example you need:

* `ansible` version 2.8 or higher - tool allows to automate deploy (see details [here](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html))
* `vagrant` - virtual machines managemet tool (see details [here](https://www.vagrantup.com/))

You also need to install `vagrant-hosts`, `vagrant-vbguest` and `vagrant-scp` plugins:

```bash
$ vagrant plugin install vagrant-hosts vagrant-vbguest vagrant-scp
```

## Hints

If you see smth like `Failed to connect to the host via ssh:` on playbook running, read this hints.

After vagrant machines start:

* delete from `~/.ssh/known_hosts` keys for `172.19.0.2` and `172.19.0.3`;
* run this commands and type `yes` to add new keys for this machines:

```bash
$ ssh vagrant@172.19.0.2
$ ssh vagrant@172.19.0.3
```

## Pack test application

We will use [`getting-started-app`](https://github.com/tarantool/cartridge-cli/tree/master/examples/getting-started-app) to show how to deploy Tarantool Cartridge application in the right way.

(If you use OS X, go to the [next section](#pack-test-application-on-os-x))

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

## Pack test application on OS X

Unfortunately, if you use OS X to develop application, you can't pack application on your local machine and then deploy it on RHEL or Debian.
The problem is that package would contain rocks (and `tarantool` binaries for Tarantool Enterprise) specific for OS X. 

The workaround is to pack application in Vagrant VM:

Create `Vagrantfile` from [this](#prepare-to-deploy) section.
Run:

```bash
$ vagrant up vm1
$ vagrant ssh vm1
[vagrant@vm1 ~]$ curl -s https://packagecloud.io/install/repositories/tarantool/1_10/script.rpm.sh | sudo bash
[vagrant@vm1 ~]$ curl -sL https://rpm.nodesource.com/setup_8.x | sudo bash -
[vagrant@vm1 ~]$ sudo yum -y install unzip git gcc cmake nodejs tarantool tarantool-devel
```

It would install Tarantool 1.10 and all tools required for Tarantool Cartridge.

Next:

```bash
[vagrant@vm1 ~]$ git clone https://github.com/tarantool/cartridge-cli
[vagrant@vm1 ~]$ cp -R cartridge-cli/examples/getting-started-app .
[vagrant@vm1 ~]$ rm -rf cartridge-cli
[vagrant@vm1 ~]$ tarantoolctl rocks install cartridge-cli
[vagrant@vm1 ~]$ .rocks/bin/cartridge pack rpm --version 1.0.0 ./getting-started-app
[vagrant@vm1 ~]$ sudo yum -y remove tarantool
[vagrant@vm1 ~]$ exit
$ vagrant scp vm1:~/getting-started-app-1.0.0-0.rpm .
```

The last command copies RPM from VM on your local machine.

Now, you can stop VM:

```bash
$ vagrant halt vm1
```

Now, we have `getting-started-app-1.0.0-0.rpm` file in current directory.
The next step is to deploy this package on servers and set up cluster.

## What does Tarantool Cartridge role do?

This is a description of deploy steps, just to understand the way Tarantool Cartridge applications have to be deployed.
You can skip this section if you are not interested in understanding how it works.

### Deploy package

The first step is to install application package on deploy server.
It would create user `tarantool` with group `tarantool` and some directories for our app:

* `/etc/tarantool/conf.d/` - directory for instances config;
* `/var/lib/tarantool/` - directory to store instances snapshots;
* `/var/run/tarantool/` - directory to store PID-files and console sockets.

Application code would be placed in `/usr/share/tarantool/${app-name}` directory.
If you use Tarantool Enterprise, `tarantool` and `tarantoolctl` binaries would be delivered with package and placed there too.
Otherwise, your RPM package has Tarantool dependency and `yum` (RPM packages manager) would install opensource Tarantool.

Package also contains `/etc/systemd/system/${app-name}.service` and `/etc/systemd/system/{app-name}@.service` [systemd unit files](https://www.digitalocean.com/community/tutorials/understanding-systemd-units-and-unit-files).

### Instances start

When you call `systemctl start getting-started-app@storage-1` systemd starts `storage-1` instance of `getting-started-app` service (see [systemd template units](https://fedoramagazine.org/systemd-template-unit-files/)).
This instance would look for it's configuration across all `/etc/tarantool/conf.d/*` yaml files sections.

See [documentation](https://www.tarantool.io/en/doc/2.2/book/cartridge/cartridge_dev/#configuring-instances) for instances configuration details.

### Setting up topology

After instances was started you need to set up cluster topology, manage auth parameters, browse application config, enable automatic failover and bootstrap vshard.
All of this actions can be performed using cluster WebUI or `cartridge` module.
To use `cartridge` Lua module you can connect to instance console using socket:

```bash
$ tarantoolctl connect /var/run/tarantool/getting-started-app.storage-1.control
tarantool> require('cartridge').is_healthy()
```

## Steps to deploy using Ansible

### Ansible

We will use [Ansible](https://www.ansible.com/use-cases/application-deployment) to deploy and configure our application.
You can read the [docs](https://docs.ansible.com/ansible/latest/index.html) to figure out how to work with this framework.
You can also find some [russian](https://habr.com/ru/post/305400/) ([or not](https://scotch.io/tutorials/getting-started-with-ansible)) getting-started guides for this framework.

### Prepare to deploy

We packed our application in `getting-started-app-1.0.0-0.rpm`.

Now, we will start 3 instances on 2 different servers, join them in 2 replicasets, bootstrap vshard, enable automatic failover, set up authorization and application config.

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
  end

  config.vm.define "vm2" do |cfg|
    cfg.vm.box = "centos/7"
    cfg.vm.network "private_network", ip: "172.19.0.3"
    cfg.vm.network "forwarded_port", guest: 8182, host: 8182
    cfg.vm.network "forwarded_port", guest: 8183, host: 8183
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
      ansible_host: 172.19.0.2  # first host
      ansible_user: vagrant

    vm2:
      ansible_host: 172.19.0.3  # second host
      ansible_user: vagrant
```

Directory structure:

```
.
├── Vagrantfile
├── getting-started-app  # this dir is not required
├── getting-started-app-1.0.0-0.rpm
├── hosts.yml
├── playbook.yml
├── tarantool-cartridge
```

### Start virtual machines

First, start virtual machines:

```bash
$ vagrant up
```

Now we will gradually upgrade our `hosts.yml` file to deploy and configure our application step-by-step.

The final version of `hosts.yml` is [here](#full-inventory).
In next steps only new sections of inventory are showed, but you always can look at the full inventory.

### Install package

To specify path to package to be deployed we need to add `cartridge_package_path` variable to our inventory file.

```yaml
---
all:
  hosts:
    ...
  vars:
    cartridge_package_path: ./getting-started-app-1.0.0-0.rpm  # path to package to deploy
```

Now, run playbook (if something went wrong, [hints](#hints) section could be helpful):

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

You can check that application files were placed in `/usr/share/tarantool/getting-started-app/` dir on virtual machines.

The same for `vm2`.

Note, that if your app uses opensource Tarantool, your package has Tarantool dependency.
Tarantool Cartridge role would enable Tarantool package repo to let Tarantool to be automatically installed with your application.
If you want to install Tarantool by yourself (e.g. from package), you can set `cartridge_enable_tarantool_repo` variable to `false`.

### Start instances

Next, configure and start instances.

Add `cartridge_instances`, `cartridge_cluster_cookie` and `cartridge_defaults` sections:

(You always can go [here](#full-inventory) to understand where to put new sections)

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
          http_port: '8182'

        - name: 'storage-1-replica'
          advertise_uri: '172.19.0.3:3302'
          http_port: '8183'

  vars:
    cartridge_app_name: getting-started-app  # application name

    cartridge_cluster_cookie: app-default-cookie  # cluster cookie
    cartridge_defaults:  # default instances parameters
      log_level: 5
```

Note, that we use `cartridge_app_name` (we don't deploy new package) instead of `cartridge_package_path`.
You can use both options, but it's required to specify at least one of them.
If `cartridge_app_name` isn't set, it would be discovered from package info.

Run the playbook again:

```bash
ansible-playbook -i hosts.yml playbook.yml
```

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
[vagrant@vm1 ~]$ ls /etc/tarantool/conf.d/
getting-started-app.storage-1.yml  getting-started-app.yml
[vagrant@vm1 ~]$ cat /etc/tarantool/conf.d/*
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
You can experiment with adding new instances and changing `cartridge_instances`, `cartridge_cluster_cookie` and `cartridge_defaults` sections.
Note, that playbook would affect only instances mentioned in config.

Instances expelling is not supported in current version, but it's coming soon.
Now, you can use Web UI to expell instances.

### Set up replicasets

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

Run playbook:

```bash
$ ansible-playbook -i hosts.yml playbook.yml
```

Then, go to http://localhost:8181/admin/cluster/dashboard.

![Replicasets](./images/replicasets.png)

Note, that `storage-1` replicaset has two roles: `storage` and it's dependency `vshard-storage`, `app-1` has roles: `api` and `vshard-router`.

Now you can't edit replicaset using Ansible, but we already have PR with this feature!

### Bootstrap Vshard

Now, when we have both `vshard-storage` and `vshard-router` replicasets, we can bootstrap vshard.
Just set `cartridge_bootstrap_vshard` flag and run the playbook again.

```yaml
---
all:
  ...
  vars:
    ...
    cartridge_bootstrap_vshard: true  # bootstrap vshard
    ...
```


Run playbook:

```bash
$ ansible-playbook -i hosts.yml playbook.yml
```

Now you can check that `Bootstrap vshard` button disappeared from the Web UI and `storage-1` replicaset `Buckets` value has been changed.

### Manage failover

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

Run playbook:

```bash
$ ansible-playbook -i hosts.yml playbook.yml
```

Check failover switcher in Web UI.
You can experiment with `cartridge_failover` value.
If this value isn't set, failover status wouldn't be affected.

### Manage auth

Our app is already configured and run, but what about security?

Let's set up auth parameters, enable Cartridge auth and create a new user:

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

Run playbook:

```bash
$ ansible-playbook -i hosts.yml playbook.yml
```

After running playbook go to http://localhost:8181/admin/cluster/dashboard and you will see the authorization form. 
Default user is `admin`, it's password is defined in `cartridge_cluster_cookie` parameter (we set `app-default-cookie`).
You also can log in using new user credentials.
Then, go to the **Users** tab and check if user was added.

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
          deleted: true  # delete user
    ...
```

Run playbook:

```bash
$ ansible-playbook -i hosts.yml playbook.yml
```

You can change authorization parameters and users configuration.
Note, that only mentioned users would be affected.

## Application config

You can configure your roles using [cluster-wide configuration](https://www.tarantool.io/en/doc/2.2/book/cartridge/cartridge_dev/#configuring-custom-roles).
To download current config go to the **Configuration files** tab in Web UI.
Most likely it's empty now.
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

Run playbook:

```bash
$ ansible-playbook -i hosts.yml playbook.yml
```

Now download config again - it would contain new sections.
You can experiment with changing section bodies.

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

Run playbook:

```bash
$ ansible-playbook -i hosts.yml playbook.yml
```

Note, that only mentioned sections would be affected.

### Final checks

Let's check if our application is working (see [this getting-started](https://github.com/tarantool/cartridge-cli/tree/master/examples/getting-started-app#application-example-based-on-tarantool-cartridge) for details).

Note, that we will use `8182` port (we specified `http_port: '8182'` for instance `app-1` running `api` role).

Create new customer:

```bash
$ curl -X POST -v -H "Content-Type: application/json" -d '{"customer_id":1, "name": "Elizaveta"}' http://localhost:8182/storage/customers/create
Note: Unnecessary use of -X or --request, POST is already inferred.
*   Trying ::1...
* TCP_NODELAY set
* Connection failed
* connect to ::1 port 8182 failed: Connection refused
*   Trying 127.0.0.1...
* TCP_NODELAY set
* Connected to localhost (127.0.0.1) port 8182 (#0)
> POST /storage/customers/create HTTP/1.1
> Host: localhost:8182
> User-Agent: curl/7.54.0
> Accept: */*
> Content-Type: application/json
> Content-Length: 38
>
* upload completely sent off: 38 out of 38 bytes
< HTTP/1.1 201 Created
< Content-length: 31
< Server: Tarantool http (tarantool v1.10.4-18-g0c10066)
< Content-type: application/json; charset=utf-8
< Connection: keep-alive
<
* Connection #0 to host localhost left intact
{"info":"Successfully created"}
```

And get it:

```bash
$ curl -X GET -v -H "Content-Type: application/json" http://localhost:8182/storage/customers/1
Note: Unnecessary use of -X or --request, GET is already inferred.
*   Trying ::1...
* TCP_NODELAY set
* Connection failed
* connect to ::1 port 8182 failed: Connection refused
*   Trying 127.0.0.1...
* TCP_NODELAY set
* Connected to localhost (127.0.0.1) port 8182 (#0)
> GET /storage/customers/1 HTTP/1.1
> Host: localhost:8182
> User-Agent: curl/7.54.0
> Accept: */*
> Content-Type: application/json
>
< HTTP/1.1 200 Ok
< Content-length: 50
< Server: Tarantool http (tarantool v1.10.4-18-g0c10066)
< Content-type: application/json; charset=utf-8
< Connection: keep-alive
<
* Connection #0 to host localhost left intact
{"accounts":[],"customer_id":1,"name":"Elizaveta"}
```

Don't forget to stop your VMs:

```bash
$ vagrant halt
```

### Afterword

For full explanation of config format read the repository README.

If you have any problems with this guide or role itself, please [create a ticket](https://github.com/tarantool/ansible-cartridge/issues/new), we will help you ASAP.

Don't hesitate to experiment with configuration, find and report some bugs.

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
          http_port: '8182'

        - name: 'storage-1-replica'
          advertise_uri: '172.19.0.3:3302'
          http_port: '8183'

  vars:
    cartridge_package_path: ./getting-started-app-1.0.0-0.rpm  # path to package to deploy
    # cartridge_app_name: getting-started-app  # can be used if package is already installed

    cartridge_cluster_cookie: app-default-cookie  # cluster cookie
    cartridge_defaults:  # default instance parameters
      log_level: 5

    cartridge_bootstrap_vshard: true  # bootstrap vshard
    cartridge_failover: true  # enable failover

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

    cartridge_auth:  # authorization parameters
      enabled: true

      cookie_max_age: 1000
      cookie_renew_age: 100

      users:
        - username: first-user
          password: first-user-password
          fullname: First Cartridge User
          email: user@cartridge.org
          # deleted: true  # delete user

    cartridge_app_config:  # application config sections
      customers:
        body:
          max-age: 100
          max-accounts-num: 5

      accounts:
        body:
          max-balance: 10000000
        # deleted: true  # delete section from config
```
