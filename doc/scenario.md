# Role Scenario

Any Ansible role contains tasks.
It's usually not possible to change set of tasks and tasks sequence.
This is not good! Sometimes we need to run only some subset of tasks,
execute tasks in a non-standard order or even add our own tasks.

To do this, we grouped tasks in thematic sets, which we called [steps](/doc/steps.md). 
Steps can be combined in list of **steps**, which we called **scenario**.

**Let's summarize:**
1. Scenario consists of steps;
2. Step consists of tasks.

## How to specify a scenario?

### Define a **scenario** (list of **steps**):

```yaml
# playbook.yml
vars:
  cartridge_scenario:
    - step_1
    - step_2
```

### Define a **scenario name** (identifier of some previously defined scenario):

```yaml
# hosts.yml
cartridge_custom_scenarios:
  my_scenario:
    - step_1
    - step_2
# playbook.yml
vars:
  cartridge_scenario_name: my_scenario
```

You can use one of [pre-defined scenarios](#pre-defined-scenarios).
Also, you can find more detailed example [here](#add-a-custom-scenario-to-gradually-update-to-a-new-version-of-TGZ)

## How to combine steps in a scenario?

Generally, you can place steps in any order,
but [steps API](/doc/steps.md) must be followed.

What does it mean?

Take a look at the [`deliver_package`](/doc/steps.md#deliver_package) and
[`update_package`](/doc/steps.md#update_package) steps. They work together:

* `deliver_package` delivers package and set `delivered_package_path` variable;
* `update_package` installs package with path from `delivered_package_path`.

These steps use `delivered_package_path` variable to communicate with each other.
Each step has variables that are required for the step work and variables that the step produces.
Descriptions of these variables for each step you can find in [steps doc](/doc/steps.md).

## Is it possible to add custom steps?

Yes, it's possible to add custom steps or rewrite the existing ones.
One of `cartridge_custom_steps_dir` (see [example](#adding-custom-step-to-scenario))
and `cartridge_custom_steps` (see [example](#importing-steps-from-different-directories))
options should be used.

## Pre-defined scenarios

### Scenario `default`

This scenario is used by default.
It contains a complete set of steps for deploying the application.

Steps:

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

### Scenario `configure_instances`

This scenario contains steps for initial deployment of instances without applying topology.

Steps:

- [deliver_package](/doc/steps.md#deliver_package)
- [update_package](/doc/steps.md#update_package)
- [update_instance](/doc/steps.md#update_instance)
- [configure_instance](/doc/steps.md#configure_instance)
- [restart_instance](/doc/steps.md#restart_instance)
- [wait_instance_started](/doc/steps.md#wait_instance_started)
- [wait_cluster_has_no_issues](/doc/steps.md#wait_cluster_has_no_issues)
- [cleanup](/doc/steps.md#cleanup)

### Scenario `configure_topology`

This scenario contains steps for editing a topology.

Steps:

- [connect_to_membership](/doc/steps.md#connect_to_membership)
- [edit_topology](/doc/steps.md#edit_topology)
- [cleanup_expelled](/doc/steps.md#cleanup_expelled)
- [wait_members_alive](/doc/steps.md#wait_members_alive)
- [wait_cluster_has_no_issues](/doc/steps.md#wait_cluster_has_no_issues)
- [cleanup](/doc/steps.md#cleanup)

### Scenario `configure_app`

This scenario contains steps for editing a configuration of application.

Steps:

- [configure_auth](/doc/steps.md#configure_auth)
- [configure_app_config](/doc/steps.md#configure_app_config)
- [bootstrap_vshard](/doc/steps.md#bootstrap_vshard)
- [configure_failover](/doc/steps.md#configure_failover)
- [wait_members_alive](/doc/steps.md#wait_members_alive)
- [wait_cluster_has_no_issues](/doc/steps.md#wait_cluster_has_no_issues)
- [cleanup](/doc/steps.md#cleanup)

To add new scenarios or replace the role scenarios with your own,
you should use `cartridge_custom_scenarios` option
(see [example](#add-a-custom-scenario-to-gradually-update-to-a-new-version-of-tgz)).

## Using `tasks_from`

You can choose a step to run on the role import using `tasks_from` option.
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

## Writing a scenario using default steps

Imagine, we want to deliver the package on machines and install it.
Let's write a simple scenario:

```yaml
# playbook.yml
vars:
  cartridge_scenario:
    - deliver_package
    - update_package
```

It looks that we will often use this scenario.
Save it to `cartridge_custom_scenarios` (e.g., in inventory) and then use by name:

```yaml
# hosts.yml
cartridge_custom_scenarios:
  deliver_and_update_package:
    - deliver_package
    - update_package
```

```yaml
# playbook.yml
vars:
  cartridge_scenario_name: deliver_and_update_package
```

## Rewriting default steps

What if we want to download the package from some repository,
but `deliver_package` step only copies the package from the local machine?

It's possible to rewrite default steps.
Create `custom_steps` directory and add `deliver_package.yml` step there:

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

Import role and specify a path to `custom_steps` directory in `cartridge_custom_steps_dir` variable:

```yaml
# deploy_application.yml

- name: Deploy application
  hosts: all
  vars:
    cartridge_custom_steps_dir: "./custom_steps"
  roles:
    - tarantool.cartridge
```

Note, that:
* [`single_instances_for_each_machine`](/doc/steps.md#role-variables-descriptions)
  variable is used to download package once for each machine;
* `delivered_package_path` variable is set to respect [API](/doc/steps.md#deliver_package);
* previously defined `deliver_and_update_package` scenario will use our custom `deliver_package`;
* `./custom_steps` path is relative to playbook path.

## Adding custom step to scenario

You can create your own step and include it to scenario.
Let's create `./custom_steps/special_magic.yml`. After that,
you can add `special_magic` step to scenario.
Just pass path to a directory where your custom steps are placed:

```yaml
- name: Deploy application
  hosts: all
  vars:
    cartridge_custom_steps_dir: "./custom_steps"
    cartridge_scenario:
      - deliver_package
      - special_magic
      - update_package
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

You can find more detailed description of rolling update [here](/doc/rolling_update.md).

## Replace a role scenario with a custom scenario

To replace any role scenario with a custom one, you only should define your own scenario
in `cartridge_custom_scenarios` with the same name as the role script.

For example, you can replace `configure_topology` scenario with
a scenario without cleanup steps:

```yaml
cartridge_custom_scenarios:
  configure_topology:
    - connect_to_membership
    - edit_topology
    - wait_members_alive
    - wait_cluster_has_no_issues
```
