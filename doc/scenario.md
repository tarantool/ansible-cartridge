# Role Scenario

Any Ansible role contains tasks.
It's usually not possible to change set of tasks and tasks sequence. This is not good!
Sometimes we need to run only some subset of tasks,
execute tasks in a non-standard order or even add our own tasks.

To do this, we grouped tasks in thematic sets, which we called [steps](/doc/steps.md). 
For example, we have default step to deliver package.

Next, we were allowed to choose which steps and in what order to run.
This is done by specifying a list of **step** names, which we called **scenario**.
For example, scenario can consist two steps:
- `deliver_package` to deliver package;
- `update_package` to extract delivered package.

**Let's summarize:**
1. Scenario consists of steps;
2. Step consists of tasks.

So, using a scenarios, you can:

- run the specified steps in any order
  by [`cartridge_scenario` variable](#configure-steps-to-launch)
  or by [`tasks_from` option](#using-tasks_from).
  Note that [API](/doc/steps.md) must be followed;
- replace the steps of the role with your own or add new steps
  by `cartridge_custom_steps_dir` or `cartridge_custom_steps` variables;
- run prepared scenario (steps list)
  by [`cartridge_scenario_name` variable](#configure-scenario-list-of-steps-to-launch);
- replace the scenario (steps list) of the role with your own or
  add new scenarios by `cartridge_custom_scenarios` variables.

## Configure steps to launch

To configure the list of steps to be launched,
you should specify a list of steps names in `cartridge_scenario` variable.
Full list of steps with descriptions your can find in [steps doc](/doc/steps.md).
For example, you can specify scenario for package update:

```yaml
vars:
  cartridge_scenario:
    - deliver_package
    - update_package
    - update_instance
    - restart_instance
    - wait_instance_started
```

To replace the steps of the role with your own or add new steps,
you should use `cartridge_custom_steps_dir` option
(see [example](#adding-custom-step-to-scenario))
or `cartridge_custom_steps` option
(see [example](#importing-steps-from-different-directories)).

## Configure scenario (list of steps) to launch

Also, to configure the list of steps to be launched,
you can specify a name of defined (by the role or by you) scenario
in `cartridge_scenario_name` variable.

There are the role scenarios (scenarios with `default` name is default):
- `default`:
  - [deliver_package](/doc/steps.md#deliver_package)
  - [update_package](/doc/steps.md#update_package)
  - [update_instance](/doc/steps.md#update_instance)
  - [configure_instance](/doc/steps.md#configure_instance)
  - [restart_instance](/doc/steps.md#restart_instance)
  - [wait_instance_started](/doc/steps.md#wait_instance_started)
  - [connect_to_membership](/doc/steps.md#connect_to_membership)
  - [edit_topology](/doc/steps.md#edit_topology)
  - [cleanup_expelled](/doc/steps.md#cleanup_expelled)
  - [configure_auth](/doc/steps.md#configure_auth)
  - [upload_app_config](/doc/steps.md#upload_app_config)
  - [configure_app_config](/doc/steps.md#configure_app_config)
  - [bootstrap_vshard](/doc/steps.md#bootstrap_vshard)
  - [configure_failover](/doc/steps.md#configure_failover)
  - [wait_members_alive](/doc/steps.md#wait_members_alive)
  - [wait_cluster_has_no_issues](/doc/steps.md#wait_cluster_has_no_issues)
  - [cleanup](/doc/steps.md#cleanup)
- `configure_instances`:
  - [deliver_package](/doc/steps.md#deliver_package)
  - [update_package](/doc/steps.md#update_package)
  - [update_instance](/doc/steps.md#update_instance)
  - [configure_instance](/doc/steps.md#configure_instance)
  - [restart_instance](/doc/steps.md#restart_instance)
  - [wait_instance_started](/doc/steps.md#wait_instance_started)
  - [wait_cluster_has_no_issues](/doc/steps.md#wait_cluster_has_no_issues)
  - [cleanup](/doc/steps.md#cleanup)
- `configure_topology`:
  - [connect_to_membership](/doc/steps.md#connect_to_membership)
  - [edit_topology](/doc/steps.md#edit_topology)
  - [cleanup_expelled](/doc/steps.md#cleanup_expelled)
  - [wait_members_alive](/doc/steps.md#wait_members_alive)
  - [wait_cluster_has_no_issues](/doc/steps.md#wait_cluster_has_no_issues)
  - [cleanup](/doc/steps.md#cleanup)
- `configure_app`:
  - [configure_auth](/doc/steps.md#configure_auth)
  - [configure_app_config](/doc/steps.md#configure_app_config)
  - [bootstrap_vshard](/doc/steps.md#bootstrap_vshard)
  - [configure_failover](/doc/steps.md#configure_failover)
  - [wait_members_alive](/doc/steps.md#wait_members_alive)
  - [wait_cluster_has_no_issues](/doc/steps.md#wait_cluster_has_no_issues)
  - [cleanup](/doc/steps.md#cleanup)

To add new scenarios or replace the role scenarios with your own,
you should use `cartridge_custom_scenarios` option
(see [example](#add-a-custom-scenario-to-gradually-update-to-a-new-version-of-TGZ)).

## Using `tasks_from`

You can select a step when importing a role.
To do this, you just need to specify in the `tasks_from` option
the name of the role step with the prefix `step_`.
Unfortunately, using this method you cannot import custom steps
(defined by `cartridge_custom_steps_dir` or `cartridge_custom_steps` options).
Also, it's impossible to use scenarios.

For example:

```yaml
- name: Step imported by 'tasks_from'
  hosts: all
  tasks:
    - name: Import step 'deliver_package'
      import_role:
        name: ansible.cartridge
        tasks_from: step_deliver_package
```

# Examples

## Adding custom step to scenario

You can create your own step and include it to scenario. Let's create `./custom_steps/special_magic.yml`. After that,
you can add `special_magic` step to scenario. Just pass path to a directory where your custom steps are placed:

```yaml
- name: Deploy application
  hosts: all
  vars:
    cartridge_custom_steps_dir: "./custom_steps"
    cartridge_scenario:
      - restart_instance
      - special_magic
  roles:
    - tarantool.cartridge
```

## Importing steps from different directories

If you want to import steps by full paths, `cartridge_custom_steps` parameter can be useful. It allows specifying
mapping between step name and path to file to import:

```yaml
cartridge_custom_steps:
  - name: 'common_special_task'
    file: './common/special_task.yml'
```

## Override task from default scenario

Sometimes we need to use default scenario, but change some steps realizations.

For example, in default scenario package specified by `cartridge_package_path` is simple copied to remote host by
step `deliver_package`. We might want to deliver package to remote machine by our own way. Let's do it!

Generally, we just need to override default `deliver_package` step.

Let's take a look on it's [API](#deliver_package). It requires two variables:

- `cartridge_package_path` that we simply specify in vars;
- `single_instances_for_each_machine` that allows us to run this task once per each machine.

As a result of this module we should set `delivered_package_path` variable
(a path of package on a remote machine).

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

- name: Deploy application
  hosts: all
  vars:
    cartridge_custom_steps_dir: "./custom_steps"
  roles:
    - tarantool.cartridge
```

## Editing topology without connecting to membership

Now there is a big problem on deploying huge clusters - [`connect_to_membership` step](#connect_to_membership) is too
long. Using scenario, we can solve this problem until it isn't solved in `cartridge`.

In variable `connect_to_membership` is used in [`set_control_instance` step](#set_control_instance) to find some instance
that is already in a cluster. This instance should be used for joining other instances (otherwise two different clusters
are created). This instance is called `control_instance` and is used for editing topology and configuring cluster (auth,
config and so on). Generally, `connect_to_membership` step can be skipped if you definitely know some instance that is
already joined to cluster. The solution is to set `cartridge_control_instance` variable manually and
remove `connect_to_membership` step from scenario:

```yaml
# edit_topology_playbook.yml

- name: Edit topology by core 1
  hosts: all
  vars:
    cartridge_scenario:
      - edit_topology
    cartridge_control_instance:
      name: core_1
      console_sock: '/var/run/tarantool/core_1.control'
  roles:
    - tarantool.cartridge
```

## Add a custom scenario to gradually update to a new version of TGZ

If you are using multiversion, then most likely you are upgrading to the new version of the package gradually:
first storages, then routers, etc. To do this, the same scenario to update the package version is used several times.
Let's remove duplication by declaring a custom scenario and then using it!

Firstly you should to define custom scenarios in hosts file:

```yaml
cartridge_multiversion: true
cartridge_package_path: "./myapp-2.0.0-0.tgz"
cartridge_custom_scenarios:
  # To deploy TGZ without instances update
  deploy_tgz:
    - deliver_package
    - update_package
  # To update instances to new TGZ
  update_instance_tgz:
    - update_instance
    - restart_instance
    - wait_instance_started
```

Then you can use them in your playbook:

```yaml
- name: Deploy new TGZ
  hosts: all
  vars:
    cartridge_scenario_name: "deploy_tgz"
  roles: tarantool.cartridge

- name: Update storages
  hosts: "*storage*"
  vars:
    cartridge_scenario_name: "update_instance_tgz"
  roles: tarantool.cartridge

- name: Update routers
  hosts: "*router*"
  vars:
    cartridge_scenario_name: "update_instance_tgz"
  roles: tarantool.cartridge
```

## Replace a role scenario with a custom scenario

To replace any role scenario with a custom one, you only should define your own scenario
in `cartridge_custom_scenarios` with the same name as the role script.

For example, you can replace `configure_topology` with a scenario without `connect_to_membership` step (see
[example for editing topology without connecting to membership](#editing-topology-without-connecting-to-membership))
```yaml
cartridge_custom_scenarios:
  configure_topology:
    - edit_topology
    - cleanup_expelled
```
