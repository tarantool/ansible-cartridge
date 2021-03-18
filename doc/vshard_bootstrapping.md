# VShard bootstrapping

The flag [`cartridge_bootstrap_vshard`](/doc/variables.md#cluster-configuration)
indicates if vshard must be bootstrapped
on the cluster.

First, it will be checked if it is reasonable to bootstrap vshard (the cluster
must have at least one `vshard-storage` replica set and at least one
`vshard-router`). If it is, vshard will be bootstrapped.
