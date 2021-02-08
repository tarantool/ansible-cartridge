def get_machine_hostname(v):
    if 'ansible_host' in v:
        return v['ansible_host']

    raise Exception(f'Instance {v["inventory_hostname"]} has not "ansible_host" option!')


def is_expelled(instance_vars):
    return instance_vars.get('expelled') is True


def is_stateboard(instance_vars):
    return instance_vars.get('stateboard') is True


def get_instance_fullname(app_name, inventory_hostname, stateboard):
    if stateboard:
        return '{}-stateboard'.format(app_name)

    return '{}.{}'.format(app_name, inventory_hostname)


def get_one_not_expelled_instance_for_machine(hostvars, play_hosts):
    machine_hostnames = set()
    instance_names = []

    for instance_name in play_hosts:
        if is_expelled(hostvars[instance_name]):
            continue

        machine_hostname = get_machine_hostname(hostvars[instance_name])
        if machine_hostname not in machine_hostnames:
            machine_hostnames.add(machine_hostname)
            instance_names.append(instance_name)

    return instance_names


def get_one_not_expelled_instance(hostvars, play_hosts):
    for i in play_hosts:
        if is_expelled(hostvars[i]) or is_stateboard(hostvars[i]):
            continue

        return i

    raise Exception('At least one play host should be non-expelled and not stateboard')


def get_control_host(control_host, hostvars, play_hosts):
    if control_host:
        return control_host

    for istance_name in play_hosts:
        instance_vars = hostvars[istance_name]
        if instance_vars.get('replicaset_alias'):
            return istance_name

    return None


def get_instance_control_sock(app_name, inventory_hostname, stateboard=False):
    instance_fullname = get_instance_fullname(app_name, inventory_hostname, stateboard)
    return '/var/run/tarantool/{}.control'.format(instance_fullname)


def get_instance_conf_file(app_name, inventory_hostname, stateboard):
    instance_fullname = get_instance_fullname(app_name, inventory_hostname, stateboard)
    return '/etc/tarantool/conf.d/{}.yml'.format(instance_fullname)


def get_app_conf_file(app_name):
    return '/etc/tarantool/conf.d/{}.yml'.format(app_name)


def get_instance_conf_section(app_name, inventory_hostname, stateboard):
    return get_instance_fullname(app_name, inventory_hostname, stateboard)


def get_instance_work_dir(app_name, inventory_hostname, stateboard):
    instance_fullname = get_instance_fullname(app_name, inventory_hostname, stateboard)
    return '/var/lib/tarantool/{}'.format(instance_fullname)


def get_instance_systemd_service(app_name, inventory_hostname, stateboard):
    if stateboard:
        return '{}-stateboard'.format(app_name)
    return '{}@{}'.format(app_name, inventory_hostname)


class FilterModule(object):
    def filters(self):
        return {
            'get_one_not_expelled_instance_for_machine': get_one_not_expelled_instance_for_machine,
            'get_one_not_expelled_instance': get_one_not_expelled_instance,
            'get_control_host': get_control_host,
            'get_instance_control_sock': get_instance_control_sock,
            'get_instance_conf_file': get_instance_conf_file,
            'get_app_conf_file': get_app_conf_file,
            'get_instance_conf_section': get_instance_conf_section,
            'get_instance_work_dir': get_instance_work_dir,
            'get_instance_systemd_service': get_instance_systemd_service,
        }
