def get_machine_identifier(v):
    return v['ansible_host'] if 'ansible_host' in v else v['inventory_hostname']


def is_expelled(instance_vars):
    return instance_vars.get('expelled') is True


def is_stateboard(instance_vars):
    return instance_vars.get('stateboard') is True


def get_instance_fullname(instance_vars):
    if instance_vars.get('stateboard'):
        return '{}-stateboard'.format(instance_vars['cartridge_app_name'])

    return '{}.{}'.format(instance_vars['cartridge_app_name'], instance_vars['inventory_hostname'])


def get_one_not_expelled_instance_for_machine(hostvars, play_hosts):
    res = []
    added_machines = {}

    for i in play_hosts:
        if is_expelled(hostvars[i]):
            continue

        machine_id = get_machine_identifier(hostvars[i])
        if machine_id not in added_machines:
            added_machines[machine_id] = True
            res.append(i)

    return res


def get_one_not_expelled_instance(hostvars, play_hosts):
    for i in play_hosts:
        if is_expelled(hostvars[i]) or is_stateboard(hostvars[i]):
            continue

        return i

    raise Exception('At least one play host should be non-expelled and not stateboard')


def get_instance_control_sock(instance_vars):
    if instance_vars.get('control_sock_path'):
        return instance_vars['control_sock_path']

    return '/var/run/tarantool/{}.control'.format(get_instance_fullname(instance_vars))


def get_instance_conf_file(instance_vars):
    return '/etc/tarantool/conf.d/{}.yml'.format(get_instance_fullname(instance_vars))


def get_app_conf_file(instance_vars):
    return '/etc/tarantool/conf.d/{}.yml'.format(instance_vars['cartridge_app_name'])


def get_instance_conf_section(instance_vars):
    return get_instance_fullname(instance_vars)


def get_instance_work_dir(instance_vars):
    return '/var/lib/tarantool/{}'.format(get_instance_fullname(instance_vars))


def get_instance_systemd_service(instance_vars):
    if instance_vars.get(stateboard):
        return '{}-stateboard'.format(instance_vars['cartridge_app_name'])
    return '{}@{}'.format(instance_vars['cartridge_app_name'], instance_vars['inventory_hostname'])


class FilterModule(object):
    def filters(self):
        return {
            'get_one_not_expelled_instance_for_machine': get_one_not_expelled_instance_for_machine,
            'get_one_not_expelled_instance': get_one_not_expelled_instance,
            'get_instance_control_sock': get_instance_control_sock,
            'get_instance_conf_file': get_instance_conf_file,
            'get_app_conf_file': get_app_conf_file,
            'get_instance_conf_section': get_instance_conf_section,
            'get_instance_work_dir': get_instance_work_dir,
            'get_instance_systemd_service': get_instance_systemd_service,
        }
