# Eval Lua code on instances

It could be useful to run code on instances by limit.

There are two steps that allow running code snippets:

* [`eval`](/doc/scenario.md#eval) runs specified snipped on each instance from play hosts.
* [`eval_on_control_instance`](/doc/scenario.md#eval_on_control_instance) runs
  specified snipped only on the control instance.

By default, result is simply saved to `eval_res` variable, but if
`cartridge_eval_with_retries` is set to `true`, than [eval with retries](#eval-with-retries) is performed.

## How to pass a code snippet?

There are two ways to specify code that should be ran:

* `cartridge_eval_file` - path to file with code;
* `cartridge_eval_body` - string with a code.

If `cartridge_eval_body` is specified, then `cartridge_eval_file` is ignored.

## How to pass args?

`cartridge_eval_args` allows to pass a list of arguments that can be used in code
as `...`.

## How to use result?

The result is saved to `eval_res` variable.
Be careful, **`eval_res` is always a list** since Tarantool returns a list of values
on eval.

## Running code from string

```yaml
- name: Eval function from string
  hosts: cluster
  roles:
    - ansible-cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario:
      - eval
    cartridge_eval_body: |
        local name, bio = ...

        return unpack({
            string.format("Hi, %s!", name),
            string.format("You are %s years old and live in %s.", bio.age, bio.city),
        })

    cartridge_eval_args:
      - 'Elizabeth'
      - age: 24
        city: 'Moscow'

- name: Print result
  hosts: cluster
  become: true
  become_user: root
  gather_facts: false
  tasks:
    - name: 'Debug result'
      debug:
        var: eval_res
```

The result of the debug task looks like this:

```
TASK [Debug result] ******************************
ok: [storage-1-leader] => {
    "eval_res": [
        "Hi, Elizabeth!",
        "You are 24 years old and live in Moscow."
    ]
}
ok: [storage-1-replica] => {
    "eval_res": [
        "Hi, Elizabeth!",
        "You are 24 years old and live in Moscow."
    ]
}
ok: [my-stateboard] => {
    "eval_res": [
        "Hi, Elizabeth!",
        "You are 24 years old and live in Moscow."
    ]
}
```

## Running code from file

The code above can be ran from a file:

```yaml
- name: Eval function from string
  hosts: cluster
  roles:
    - ansible-cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario:
      - eval
    cartridge_eval_file: 'my_snippet.lua'
    cartridge_eval_args:
      - 'Elizabeth'
      - age: 24
        city: 'Moscow'
```

## Eval with retries

If `cartridge_eval_with_retries` is set, that `eval` expects that function
return `res, err`.
It retries until `err` is received.

It can be useful to perform some checks in Lua code and wait until some condition is met.

Retries and delay can be configured:
- `cartridge_eval_retries` (`number`, default: `3`) number of eval retries;
- `cartridge_eval_delay` (`number`, default: `5`)  - eval retries delay;

```yaml
- name: Eval with retries
  hosts: cluster
  roles:
    - ansible-cartridge
  become: true
  become_user: root
  gather_facts: false
  vars:
    cartridge_scenario:
      - eval
    cartridge_eval_with_retries: true
    cartridge_eval_retries: 10
    cartridge_eval_delay: 1
    cartridge_eval_body: |
      local checkpoint_is_in_progress = box.info().gc().checkpoint_is_in_progress
      if checkpoint_is_in_progress then
        return nil, "Checkpoint is still in progress"
      end

      return true
```
