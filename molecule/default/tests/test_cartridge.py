import os
import yaml

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')


def check_conf_file(conf_file, conf_section, conf):
    assert conf_file.exists
    assert conf_file.user == 'tarantool'
    assert conf_file.group == 'tarantool'

    conf_file_dict = yaml.load(conf_file.content_string, Loader=yaml.FullLoader)

    assert conf_section in conf_file_dict
    assert conf_file_dict[conf_section] == conf


def test_myapp_instances_status_and_config(request, host):
    ansible_vars = host.ansible.get_variables()
    instances = ansible_vars['cartridge_config']['instances']
    default_conf = ansible_vars['cartridge_config_defaults']

    app_name = 'myapp'

    for instance in instances:
        inst_name = instance['name']

        service = host.service('{}@{}'.format(app_name, inst_name))
        assert service.is_running

        conf_file_path = '/etc/tarantool/conf.d/{}.{}.yml'.format(app_name, inst_name)
        conf_file = host.file(conf_file_path)
        conf_section = '{}.{}'.format(app_name, inst_name)

        del instance['name']

        check_conf_file(conf_file, conf_section, instance)

    default_conf_file_path = '/etc/tarantool/conf.d/{}.yml'.format(app_name)
    default_conf_file = host.file(default_conf_file_path)
    default_conf_file_section = app_name

    check_conf_file(default_conf_file, default_conf_file_section, default_conf)
