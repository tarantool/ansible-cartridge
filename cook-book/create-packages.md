# Application package

To use the `tarantool.cartridge` role you need an application package.

Requirements:
* [Cartridge CLI](https://github.com/tarantool/cartridge-cli#installation).

## Create application

If you already have Tarantool Cartridge-based application, just use it.

Otherwise, create simple Cartridge application:

```bash
cartridge create --name myapp
cd myapp
```

## Pack application

The role supports three types of packages - RPM, DEB ang TGZ.
Use the one you need.

```bash
cartridge pack rpm|deb|tgz --version 1.0.0

# for OS X:

cartridge pack rpm|deb|tg --version 1.0.0 --use-docker
```

After that you have `myapp-1.0.0-0.{rpm,deb,tar.gz}` in the application root.

Copy this file to the directory with playbook or specify the correct path in
`hosts.yml`. By default, all cook-book inventories expect package in the current
directory.
