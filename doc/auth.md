# Configuring auth

[`cartridge_auth`](/doc/variables.md#cluster-configuration)
 parameter is used to specify authorization settings:

- `enabled`(`boolean`) - indicates if authorization is enabled;
- `cookie_max_age`(`number`) - number of seconds until the authorization
  cookie expires;
- `cookie_renew_age`(`number`) - update the provided cookie if it's older
  than this age.
- `users`(`list-of-dicts`) - list of users to be configured on the
  cluster (described below).

**Users configuration:**

- `username`(`string`, required);
- `password`(`string`) - is required for new users;
- `fullname`(`string`);
- `email`(`string`);
- `deleted`(`boolean`) - indicates if the user must be removed.

**Note:** The default user `admin` can't be managed here.

*Example:*

```yaml
cartridge_auth:
  enabled: true   # enable authorization

  cookie_max_age: 1000
  cookie_renew_age: 100

  users:  # cartridge users to set up
    - username: tarantool
      password: tarantool-the-best
      fullname: Tarantool The Best
      email: tarantool@tarantool.org

    - username: bad-guy
      deleted: true  # marked to be deleted
```
