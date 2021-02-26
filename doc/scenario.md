# Role Scenario

The role uses a scenario to determine what to do. Scenario consists of steps that can be configured.

Using a scenario of steps, you can:

- run the specified steps in any order, but API must be followed (with `cartridge_scenario`);
- replace the steps of the role with your own or add new steps
  (with `cartridge_custom_steps_dir` or `cartridge_custom_steps`).

## Steps

In `cartridge_scenario` you should specify names of steps. The default scenario includes the following steps:

- [deliver_package](#deliver_package)
- [update_package](#update_package)
- [update_instance](#update_instance)
- [configure_instance](#configure_instance)
- [restart_instance](#restart_instance)
- [wait_instance_started](#wait_instance_started)
- [connect_to_membership](#connect_to_membership)
- [edit_topology](#edit_topology)
- [cleanup_expelled](#cleanup_expelled)
- [configure_auth](#configure_auth)
- [configure_app_config](#configure_app_config)
- [bootstrap_vshard](#bootstrap_vshard)
- [configure_failover](#configure_failover)

There are additional steps that are not included in the default scenario, but can be used in a custom one:

- [set_control_instance](#set_control_instance)
- [rotate_dists](#rotate_dists)

To replace the steps of the role with your own or add new steps, you should use `cartridge_custom_steps_dir`
or `cartridge_custom_steps` options.

## Examples

### Adding custom step to scenario

You can create your own step and include it to scenario. Let's create `./custom_steps/special_magic.yml`. After that,
you can add `special_magic` step to scenario. Just pass path to a directory where your custom steps are placed:

```yaml
- name: My playbook
  hosts: all
  tasks:
    - name: Deploy application
      import_role:
        name: tarantool.cartridge
      vars:
        cartridge_custom_steps_dir: "./custom_steps"
        cartridge_scenario:
          - restart_instance
          - special_magic
```

### Importing steps from different directories

If you want to import steps by full paths, `cartridge_custom_steps` parameter can be useful. It allows specifying
mapping between step name and path to file to import:

```yaml
cartridge_custom_steps:
  - name: 'common_special_task'
    file: './common/special_task.yml'
```

### Override task from default scenario

Sometimes we need to use default scenario, but change some steps realizations.

For example, in default scenario package specified by `cartridge_package_path` is simple copied to remote host by
step `deliver_package`. We might want to deliver package to remote machine by our own way. Let's do it!

Generally, we just need to override default `deliver_package` step.

Let's take a look on it's [API](#deliver_package). It requires two variables:

- `cartridge_package_path` that we simply specify in vars;
- `single_instances_for_each_machine` that allows us to run this task once per each machine.

As a result of this module we should set `delivered_package_path` variable
(a path of package on remote machine).

Now, choose a directory where our custom steps are placed, for example `./custom_steps`.

Then create `./custom_steps/deliver_package.yml` and describe a way to deliver package:

```yaml
# ./custom_steps/deliver_package.yml

- when:
    - cartridge_package_path is not none
    - inventory_hostname in single_instances_for_each_machine
  tags: cartridge-instances
  block:
    - name: 'Download package'
      get_url:
        url: 'https://some-server/myapp-1.0.0-0.rpm'
        dest: '/tmp'
      register: downloaded_package

    - name: 'Set delivered package path'
      set_fact:
        delivered_package_path: '{{ downloaded_package.dest }}'
```

Import role and say where to find our custom steps:

```yaml
# deploy_application.yml

- name: My playbook
  hosts: all
  tasks:
    - name: Deploy application
      import_role:
        name: tarantool.cartridge
      vars:
        cartridge_custom_steps_dir: "./custom_steps"
```

### Editing topology without connecting to membership

Now there is a big problem on deploying huge clusters - [`connect_to_membership` step](#connect_to_membership) is too
long. Using scenario, we can solve this problem until it isn't solved in `cartridge`.

In fact `connect_to_membership` is used in [`set_control_instance` step](#set_control_instance) to find some instance
that is already in cluster. This instance should be used for joining other instances (otherwise two different clusters
are created). This instance is called `control_instance` and is used for editing topology and configuring cluster (auth,
config and so on). Generally, `connect_to_membership` step can be skipped if you definitely know some instance that is
already joined to cluster. The solution is to set `control_instance` fact manually and remove `connect_to_membership`
step from scenario:

```yaml
# edit_topology_playbook.yml

- name: Edit topology of my cluster
  hosts: all
  tasks:
    - name: Edit topology by core 1
      import_role:
        name: tarantool.cartridge
      vars:
        cartridge_scenario:
          - edit_topology
        control_instance:
          name: core_1
          console_sock: '/var/run/tarantool/core_1.control'
```

## Role Facts Descriptions

Role facts are established during preparation, so you can use them at any step.

List of facts:

- `instance_info` - information for a current instance. It's a dictionary with fields:
  - `app_conf_file` - path to file with application config;
  - `conf_file` - path to file with instance config;
  - `instance_id` - ID of instance (e.g. for section name in config file);
  - `console_sock` - path to control socket of instance;
  - `pid_file` - path to pid file of instance;
  - `work_dir` - path to working directory of instance;
  - `tmpfiles_conf` - path to config file of temporary files;
  - `dist_dir` - path to directory of distributed package;
  - `instance_dist_dir` - path to instance link to distributed package;
- `single_instances_for_each_machine` - list of instances (Ansible hosts), one for each physical machine. Can be used,
  for example, in `delegate_to`;
- `not_expelled_instance` - information about one not expelled instance. It's a dictionary with fields:
  - `name` - instance name (Ansible host);
  - `console_sock` - path to control socket of instance;
- `scenario_steps` - description of scenario steps. It's a dictionary with fields:
  - `name` - name of step;
  - `path` - path to YAML file of step.

## Role Steps Description

### deliver_package

Delivery of the application package to physical machines.

Input facts (set by role):

- `single_instances_for_each_machine` - list of instances (Ansible hosts), one for each physical machine.

Input facts (set by config):

- `cartridge_package_path` - path to file of package to delivery.

Output facts:

- `delivered_package_path` - remote path to file of delivered package.

### update_package

Install the delivered package on physical machines.

Input facts (set by role):

- `single_instances_for_each_machine` - list of instances (Ansible hosts), one for each physical machine;
- `delivered_package_path` - remote path to file of delivered package.

Input facts (set by config):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions));
- `cartridge_app_name` - application name;
- `cartridge_enable_tarantool_repo` - indicates if Tarantool repository should be enabled;
- `cartridge_install_tarantool_for_tgz` - indicates if Tarantool should be enabled when use TGZ package;
- `cartridge_multiversion` - indicates that multiple package versions is enabled;
- `cartridge_configure_tmpfiles` - indicates that tmpfiles config should be configured;
- `cartridge_configure_systemd_unit_files` - indicates that systemd Unit files should be configured;
- `cartridge_app_user` - user which will own the links;
- `cartridge_app_group` - group which will own the links;
- `cartridge_run_dir` - path to directory of instances sockets;
- `cartridge_data_dir` - path to directory of instances data;
- `cartridge_conf_dir` - path to directory of instances application configs;
- `cartridge_app_install_dir` - path to directory with application distributions;
- `cartridge_app_instances_dir` - path to directory with instances links to
  distributions (see [multiversion approach doc](/doc/multiversion.doc)).

Output facts:

- `package_info` - information about delivered package. It's a dictionary with fields:
  - `name` - application name;
  - `tnt_version` - version of Tarantool required by application;
  - `type` - type of package (`rpm`, `deb` or `tgz`).
- `systemd_units_info` - information for systemd Units files. It's a dictionary with fields:
  - `stateboard_name` - ID of stateboard instance;
  - `app_unit_file` - filename of application Unit file;
  - `stateboard_unit_file` - filename of stateboard Unit file;
  - `instance_work_dir` - path to working directory of instance;
  - `stateboard_work_dir` - path to working directory of stateboard;
  - `instance_pid_file` - path to pid file of instance;
  - `stateboard_pid_file` - path to pid file of stateboard;
  - `instance_console_sock` - path to control socket of instance;
  - `stateboard_console_sock` - path to control socket of stateboard;
  - `instance_entrypoint` - path to Lua entrypoint file of instance;
  - `stateboard_entrypoint` - path to Lua entrypoint file of stateboard;
  - `instance_tarantool_binary` - path Tarantool binary file of instance;
  - `stateboard_tarantool_binary` - path Tarantool binary file of stateboard.

### update_instance

Update instance links for a new version of package (if
[multiversion approach](/doc/multiversion.md) is enabled).

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `cartridge_multiversion` - indicates that
  [multiversion approach](/doc/multiversion.md) is enabled;
- `cartridge_app_user` - user which will own the links;
- `cartridge_app_group` - group which will own the links.

### configure_instance

Configure instance in runtime and change instance config.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `config` - instance configuration ([more details here](/README.md#instances));
- `restarted` - if instance should be restarted or not (user forced decision);
- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `cartridge_app_name` - application name;
- `cartridge_cluster_cookie` - cluster cookie for all cluster instances;
- `cartridge_defaults` - default configuration parameters values for instancesж
- `cartridge_app_user` - user which will own the links;
- `cartridge_app_group` - group which will own the links.

Output facts:

- `needs_restart` - if instance should be restarted to apply code or configuration changes.

### restart_instance

Restart instance if it should be restarted.

Input facts (set by role):

- `needs_restart` - if instance should be restarted to apply code or configuration changes;
- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `restarted` - if instance should be restarted or not (user forced decision).

### wait_instance_started

Wait until instance is fully started.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `instance_start_timeout` - time in seconds to wait for instance to be started;
- `cartridge_wait_buckets_discovery` - indicates if routers should wait for buckets discovery after vshard bootstrap.

### connect_to_membership

Connect instance to membership.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `cartridge_app_name` - application name;
- `config` - instance configuration ([more details here](/README.md#instances)).

### set_control_instance

Find some instance that is already in cluster. If there is no such instance, use one of instances that should be joined.

**This step should be launched only after `connect_to_membership` step. Otherwise, 2 clusters may be created!**

Input facts (set by role):

- `not_expelled_instance` - information about one not expelled instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `replicaset_alias` - replicaset alias, will be displayed in Web UI;
- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Output facts:

- `control_instance` - information about control instance. It's a dictionary with fields:
  - `name` - Ansible name of instance;
  - `console_sock` - path to control socket of instance.

### edit_topology

Edit topology of replicasets.

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance)).

Input facts (set by config):

- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `replicaset_alias` - replicaset alias, will be displayed in Web UI;
- `roles` - roles to be enabled on the replicaset;
- `failover_priority` - failover priority order;
- `all_rw` - indicates that that all servers in the replicaset should be read-write;
- `weight` - vshard replicaset weight;
- `vshard_group` - vshard group.

### cleanup_expelled

Cleanup files if instance is expelled.

Input facts (set by role):

- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `expelled` - indicates if instance must be expelled from topology;

### configure_auth

Configure application authentication settings.

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance)).

Input facts (set by config):

- `cartridge_auth` - authorization configuration.

### configure_app_config

Configure application configuration.

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance)).

Input facts (set by config):

- `cartridge_app_config` - application config sections to patch.

### bootstrap_vshard

Bootstrap VShard in cluster.

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance));
- `instance_info` - information for a current instance ([more details here](#role-facts-descriptions)).

Input facts (set by config):

- `expelled` - indicates if instance must be expelled from topology;
- `stateboard` - indicates that the instance is a stateboard;
- `cartridge_bootstrap_vshard` - indicates if vshard should be bootstrapped;
- `instance_discover_buckets_timeout` - time in seconds to wait for instance to discover buckets;
- `cartridge_wait_buckets_discovery` - indicates if routers should wait for buckets discovery after vshard bootstrap.

### configure_failover

Configure application failover.

*If `control_instance` is not defined then [set_control_instance](#set_control_instance) will run.*

Input facts (set by role):

- `control_instance` - information about control instance ([more details here](#set_control_instance)).

Input facts (set by config):

- [DEPRECATED] `cartridge_failover` - indicates if eventual failover should be enabled or disabled;
- `cartridge_failover_params` - failover parameters.

### rotate_dists

Rotate application distributions.

When [multiversion approcah](/doc/multiversion.md) is used, each new application
version is added to `cartridge_app_install_dir`.
This step removes redundant distribution.

Input facts (set by config):

- `cartridge_app_name` - application name;
- `cartridge_app_install_dir` - path to directory where application distributions
  are placed;
- `cartridge_dists_retention_num` - number of dists that should be kept.
