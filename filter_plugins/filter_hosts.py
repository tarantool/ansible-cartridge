def get_machine_identifier(v):
    return v['ansible_host'] if 'ansible_host' in v else v['inventory_hostname']


def is_expelled(instance_vars):
    return instance_vars.get('expelled') is True


def is_stateboard(instance_vars):
    return instance_vars.get('stateboard') is True


def get_instance_fullname(app_name, inventory_hostname, stateboard):
    if stateboard:
        return '{}-stateboard'.format(app_name)

    return '{}.{}'.format(app_name, inventory_hostname)


def one_not_expelled_instance_for_machine(hostvars, play_hosts):
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


def one_not_expelled_instance(hostvars, play_hosts):
    for i in play_hosts:
        if is_expelled(hostvars[i]) or is_stateboard(hostvars[i]):
            continue

        return i

    raise Exception('At least one play host should be non-expelled and not stateboard')


def instance_control_sock(app_name, inventory_hostname, stateboard=False):
    instance_fullname = get_instance_fullname(app_name, inventory_hostname, stateboard)
    return '/var/run/tarantool/{}.control'.format(instance_fullname)


def instance_conf_file(app_name, inventory_hostname, stateboard=False):
    instance_fullname = get_instance_fullname(app_name, inventory_hostname, stateboard)
    return '/etc/tarantool/conf.d/{}.yml'.format(instance_fullname)


def conf_section_name(app_name, inventory_hostname, stateboard=False):
    return get_instance_fullname(app_name, inventory_hostname, stateboard)


def systemd_service_name(app_name, inventory_hostname, stateboard=False):
    if stateboard:
        return '{}-stateboard'.format(app_name)
    return '{}@{}'.format(app_name, inventory_hostname)


class FilterModule(object):
    def filters(self):
        return {
            'one_not_expelled_instance_for_machine': one_not_expelled_instance_for_machine,
            'one_not_expelled_instance': one_not_expelled_instance,
            'instance_control_sock': instance_control_sock,
            'instance_conf_file': instance_conf_file,
            'conf_section_name': conf_section_name,
            'systemd_service_name': systemd_service_name,
        }
