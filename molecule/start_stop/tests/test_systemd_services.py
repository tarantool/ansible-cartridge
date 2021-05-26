from importlib.machinery import SourceFileLoader
utils = SourceFileLoader("utils", "./molecule/common/tests/utils.py").load_module()


testinfra_hosts = utils.get_testinfra_hosts()


def test_services_status(host):
    app_name = utils.get_app_name()

    machine_instances = utils.get_machine_instances(host)
    assert machine_instances

    for instance in machine_instances:
        instance_vars = utils.get_instance_vars(instance)
        instance_name = instance_vars['inventory_hostname']

        service_name = '%s@%s' % (app_name, instance_name)
        service = host.service(service_name)

        running_instances = ['instance-started', 'instance-restarted', 'instance-restarted-force']
        if instance_name == 'instance-stopped':
            assert not service.is_running
            assert not service.is_enabled
        elif instance_name in running_instances:
            assert service.is_running
            assert service.is_enabled
        else:
            assert False
