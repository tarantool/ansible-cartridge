#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes


argument_spec = {
    'hosts': {'required': True, 'type': 'list'},
    'hostvars': {'required': True, 'type': 'dict'}
}

INSTANCE_REQUIRED_PARAMS = ['name', 'advertise_uri', 'http_port']
REPLICASET_REQUIRED_PARAMS = ['name', 'instances', 'roles']


def validate_config(params):
    all_instances = {}
    all_replicasets = {}

    # To check if this params are equal for all hosts
    app_name = None
    package_path = None
    cluster_cookie = None

    for host in params['hosts']:
        host_vars = params['hostvars'][host]

        # Check if at least one of app_name and package_path specified
        if 'cartridge_app_name' not in host_vars and 'cartridge_package_path' not in host_vars:
            errmsg = 'At least one of `cartridge_app_name` and `cartridge_package_path` must be specified'
            return ModuleRes(success=False, msg=errmsg)

        # Check app_name
        if app_name is not None:
            if 'cartridge_app_name' in host_vars and host_vars['cartridge_app_name'] != app_name:
                errmsg = '`cartridge_app_name` name must be the same for all hosts'
                return ModuleRes(success=False, msg=errmsg)
        elif 'cartridge_app_name' in host_vars:
            app_name = host_vars['cartridge_app_name']

        if 'cartridge_instances' in host_vars:
            # Check cluster cookie
            if 'cartridge_cluster_cookie' not in host_vars:
                errmsg = '`cartridge_cluster_cookie` must be specified'
                return ModuleRes(success=False, msg=errmsg)

            # Check if cookie is the same for all hosts
            if cluster_cookie is not None:
                if host_vars['cartridge_cluster_cookie'] != cluster_cookie:
                    errmsg = 'Cluster cookie must be the same for all hosts'
                    return ModuleRes(success=False, msg=errmsg)
            else:
                cluster_cookie = host_vars['cartridge_cluster_cookie']

        if 'cartridge_defaults' in host_vars:
            if 'cluster_cookie' in host_vars['cartridge_defaults']:
                errmsg = 'Cluster cookie must be specified in `cartridge_cluster_cookie`, not in `cartridge_defaults`'
                return ModuleRes(success=False, msg=errmsg)

        # Check package_path
        if package_path is not None:
            if 'cartridge_package_path' in host_vars and host_vars['cartridge_package_path'] != package_path:
                errmsg = '`cartridge_package_path` name must be the same for all hosts'
                return ModuleRes(success=False, msg=errmsg)
        elif 'cartridge_package_path' in host_vars:
            package_path = host_vars['cartridge_package_path']

        # Check instances
        if 'cartridge_instances' in host_vars:
            for instance in host_vars['cartridge_instances']:

                # Check if all required params are specified
                for p in INSTANCE_REQUIRED_PARAMS:
                    if p not in instance:
                        errmsg = 'Parameter "{}" is required for all instances in `cartridge_instances`'.format(p)
                        return ModuleRes(success=False, msg=errmsg)

                # Check if cluster_cookie is not specified
                if 'cluster_cookie' in instance:
                    errmsg = '`cluster_cookie is specified for instance "{}"`.'.format(instance['name']) + \
                        'It must be specified ONLY in `cartridge_cluster_cookie` variable.'
                    return ModuleRes(success=False, msg=errmsg)

                # Check if instance name is unique
                if instance['name'] in all_instances:
                    errmsg = 'Duplicate instance name: "{}"'.format(instance['name'])
                    return ModuleRes(success=False, msg=errmsg)

                # Save instance info
                all_instances[instance['name']] = instance

        # Check replicasets
        if 'cartridge_replicasets' in host_vars:
            for replicaset in host_vars['cartridge_replicasets']:
                # Check if all required params are specified
                for p in REPLICASET_REQUIRED_PARAMS:
                    if p not in replicaset:
                        errmsg = 'Parameter "{}" is required for all replicasets in `cartridge_replicasets`'.format(p)
                        return ModuleRes(success=False, msg=errmsg)

                # Check if replicaset name is unique
                if replicaset['name'] in all_replicasets:
                    if all_replicasets[replicaset['name']] != replicaset:
                        errmsg = 'Duplicate replicaset name: "{}"'.format(replicaset['name'])
                        return ModuleRes(success=False, msg=errmsg)

                if 'leader' not in replicaset:
                    if len(replicaset['instances']) > 1:
                        errmsg = 'Leader must be specified for replicaset with more than one instance ("{}")'.format(replicaset['name'])
                        return ModuleRes(success=False, msg=errmsg)

                # Save replicaset info
                all_replicasets[replicaset['name']] = replicaset

    # Check if all replicasets instances are described in `cartridge_instances`
    #  and one instance belongs to only one replicaset
    for rname, replicaset in all_replicasets.items():
        for replicaset_instance in replicaset['instances']:
            if replicaset_instance not in all_instances:
                errmsg = 'Replicaset "{}" contains instance "{}" not described in `cartridge_instances`'.format(
                    rname, replicaset_instance
                )
                return ModuleRes(success=False, msg=errmsg)

            if 'belongs_to' not in all_instances[replicaset_instance]:
                all_instances[replicaset_instance]['belongs_to'] = rname
            else:
                errmsg = 'Instance "{}" is configured to belong to "{}" and "{}" replicasets.'.format(
                    replicaset_instance, rname, all_instances[replicaset_instance]['belongs_to']
                )
                return ModuleRes(success=False, msg=errmsg)

    return ModuleRes(success=True, changed=False, meta={'all_instances': all_instances})


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = validate_config(module.params)

    if res.success == True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
