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
