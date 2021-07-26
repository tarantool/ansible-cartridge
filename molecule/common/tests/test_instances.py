import os

from yaml import CLoader as Loader

import utils

testinfra_hosts = utils.get_testinfra_hosts()


def check_conf_file(conf_file, instance_id, conf):
    assert conf_file is not None, 'Config file should exists'
    assert conf_file.exists
    assert conf_file.user == 'tarantool'
    assert conf_file.group == 'tarantool'

    loader = Loader(conf_file.content_string)
    conf_file_dict = loader.get_data()

    assert instance_id in conf_file_dict
    assert conf_file_dict[instance_id] == conf


def test_systemd_services(host):
    app_name = utils.get_app_name()

    machine_instances = utils.get_machine_instances(host)
    assert machine_instances

    for instance in machine_instances:
        instance_vars = utils.get_instance_vars(instance)

        instance_name = instance_vars['inventory_hostname']

        if not utils.instance_is_stateboard(instance_vars):
            service_name = '%s@%s' % (app_name, instance_name)
        else:
            service_name = '%s-stateboard' % app_name

        service = host.service(service_name)

        if utils.instance_is_expelled(instance_vars):
            assert not service.is_running
            assert not service.is_enabled
        else:
            assert service.is_running
            assert service.is_enabled


def test_dirs(host):
    app_name = utils.get_app_name()

    machine_instances = utils.get_machine_instances(host)
    assert machine_instances

    for instance in machine_instances:
        instance_vars = utils.get_instance_vars(instance)
        instance_id = utils.get_instance_id(app_name, instance_vars)

        conf_dir = instance_vars.get('cartridge_conf_dir', '/etc/tarantool/conf.d')
        run_dir = instance_vars.get('cartridge_run_dir', '/var/run/tarantool')
        data_dir = instance_vars.get('cartridge_data_dir', '/var/lib/tarantool')

        install_dir = instance_vars.get('cartridge_app_install_dir', '/usr/share/tarantool')
        instances_dir = instance_vars.get('cartridge_app_instances_dir', '/usr/share/tarantool')

        multiversion = instance_vars.get('cartridge_multiversion', False)

        if not multiversion:
            dist_dir_path = os.path.join(install_dir, app_name)
        else:
            package_path = instance_vars.get('cartridge_package_path')
            package_basename = os.path.basename(package_path)
            package_name_version, ext = os.path.splitext(package_basename)
            if ext == '.gz' and package_name_version.endswith('.tar'):
                package_name_version, _ = os.path.splitext(package_name_version)

            dist_dir_path = os.path.join(install_dir, package_name_version)

        dist_dir = host.file(dist_dir_path)
        assert dist_dir.exists

        if multiversion:
            instance_dist_dir = host.file(os.path.join(instances_dir, instance_id))
            assert instance_dist_dir.exists
            assert instance_dist_dir.is_symlink
            assert instance_dist_dir.linked_to == dist_dir_path

        conf_file = host.file(os.path.join(conf_dir, '%s.yml' % instance_id))
        default_conf_file = host.file(os.path.join(conf_dir, '%s.yml' % app_name))
        pid_file = host.file(os.path.join(run_dir, '%s.pid' % instance_id))
        console_sock_file = host.file(os.path.join(run_dir, '%s.control' % instance_id))
        work_dir_file = host.file(os.path.join(data_dir, instance_id))

        if not utils.instance_is_expelled(instance_vars):
            assert conf_file.exists
            assert default_conf_file.exists
            assert console_sock_file.exists
            assert work_dir_file.exists
        else:
            assert not conf_file.exists
            assert not pid_file.exists
            assert not console_sock_file.exists
            assert not work_dir_file.exists


def test_configs(host):
    app_name = utils.get_app_name()

    machine_instances = utils.get_machine_instances(host)
    assert machine_instances

    default_conf = utils.get_cluster_var('cartridge_defaults', default={})

    not_save_cookie_in_app_config = utils.get_cluster_var('cartridge_not_save_cookie_in_app_config', False)
    if not not_save_cookie_in_app_config:
        default_conf.update(cluster_cookie=utils.get_cluster_cookie())

    default_conf_file = None
    for instance in machine_instances:
        instance_vars = utils.get_instance_vars(instance)
        instance_id = utils.get_instance_id(app_name, instance_vars)

        instance_conf = instance_vars['config']
        if instance_conf.get('memtx_memory') == '{{ common_memtx_memory }}':
            instance_conf['memtx_memory'] = 268436000

        conf_dir = instance_vars.get('cartridge_conf_dir', '/etc/tarantool/conf.d')

        conf_file = host.file(os.path.join(conf_dir, '%s.yml' % instance_id))
        default_conf_file = host.file(os.path.join(conf_dir, '%s.yml' % app_name))

        if not utils.instance_is_expelled(instance_vars):
            check_conf_file(conf_file, instance_id, instance_conf)

    check_conf_file(default_conf_file, app_name, default_conf)


def test_instances():
    configured_instances = utils.get_configured_instances()

    # Select one instance to be control
    admin_api_url = utils.get_admin_api_url()

    # Get all started instances
    query = '''
        query {
          servers {
            uri
            alias
            zone
          }
        }
    '''
    session = utils.get_authorized_session()
    response = session.post(admin_api_url, json={'query': query})
    data = utils.get_response_data(response)

    started_instances = data['servers']
    started_instances = {i['alias']: i for i in started_instances}

    # filter out expelled instances and stateboard
    configured_instances = {
        i: instance_vars for i, instance_vars in configured_instances.items()
        if not utils.instance_is_expelled(instance_vars) and not utils.instance_is_stateboard(instance_vars)
    }

    # Check if all configured instances are started and available
    assert len(configured_instances) == len(started_instances)
    assert set(configured_instances.keys()) == set(started_instances.keys())
    assert all([
        configured_instances[i]['config']['advertise_uri'] == started_instances[i]['uri']
        for i in configured_instances
    ])

    assert all([
        configured_instances[i].get('zone') == started_instances[i]['zone']
        for i in configured_instances
    ])
