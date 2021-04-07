# Application package

To use the `tarantool.cartridge` role you need an application package.

Requirements:
* [Cartridge CLI](https://github.com/tarantool/cartridge-cli#installation).

## Create application

If you already have Tarantool Cartridge-based application, just use it.
**Note**, that in this case you should change `cartridge_app_name` value in
inventory you use.

Otherwise, create simple Cartridge application:

```bash
cartridge create --name myapp
cd myapp
```

## Pack application

The role supports three types of packages - RPM, DEB and TGZ.
Choose the one that suits you best

**Note** that version is specified.
It avoids including commit hash in package name to make configuration
files determined.

```bash
cartridge pack rpm|deb|tgz --version 1.0.0

# for OS X:
cartridge pack rpm|deb|tgz --version 1.0.0 --use-docker
```

After that you will have `myapp-1.0.0-0.{rpm,deb,tar.gz}` in the application root.

Copy this file to the directory with playbook or specify the correct path in
`hosts.yml`. By default, all cook-book inventories expect
`myapp-1.0.0-0.rpm` package in the current directory.
