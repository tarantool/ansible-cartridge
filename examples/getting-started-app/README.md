# Deploy example Tarantool Cartridge Application

Here we will show you how to easily deploy your Tarantool Cartridge application, set up topology and configure cluster.

We will use [`getting-started-app`](https://github.com/tarantool/cartridge-cli/tree/master/examples/getting-started-app) to show how to deploy Tarantool Cartridge application in right way.

## Setting up the environment

**TODO**

## Steps to deploy manually

**TODO:** describe steps required to deploy app (to understand what does this role do and how to configure it in right way): 

* Application package: files and users created by package, where would application code be placed, tarantool binary (for enterprise), systemd unit files, tmpfs.
* Package installation
* Start instances: instantiated unit files, `cartridge.argparse`, instances config (where should it be placed, structure, priority)
* `systemd` service: start and enable, how to use `journalctl`
* console socket? (maybe it makes sense to describe how does ansible configure instances)
* auth - links to cartridge doc, possible errors, short description.
* application config - the same as above.
* setting up topology: using WebUI or lua `cartridge` module (console sock here?)

## Steps to deploy using ansible

### Ansible

**TODO:** short description, links to manuals (hope they exist), maybe hightlight some things (like host_vars, group_vars, become, remote_user etc)

### Dir structure

**TODO**

### Example topology

**TODO:** come up with an example topology (probably steal it from getting-started-app), describe it.

### Instances config

**TODO:** describe how to deploy package, start instances and check if it's all OK.
Describe how to edit instances.

### Replicasets

**TODO:** describe how to configure replicasets, how to edit them (hope edit-topology would be merged) and check if it's all OK.

### Vshard

**TODO:** the same as above.

### Failover

**TODO:** the same as above.

### Auth

**TODO:** the same as above.

### Application config

**TODO:** the same as above + sections format example.

(find the Cartridge doc for all this things)

