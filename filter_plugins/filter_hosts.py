import os

def get_machine_identifier(v):
    return v['ansible_host'] if 'ansible_host' in v else v['inventory_hostname']


def is_expelled(instance_vars):
    return instance_vars.get('expelled') is True


def is_stateboard(instance_vars):
    return instance_vars.get('stateboard') is True


def is_started(instance_vars):
    return instance_vars.get('instance_is_started') is True


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


def get_instances_on_machine(hostvars, ansible_host):
    res = []
    for i in hostvars:
        if i['ansible_host'] == ansible_host:
            res.append(i)
    return res


def get_one_not_expelled_instance(hostvars, play_hosts):
    for i in play_hosts:
        if is_expelled(hostvars[i]) or is_stateboard(hostvars[i]) or not is_started(hostvars[i]):
            continue

        return i

    raise Exception('At least one play host should be non-expelled and not stateboard')


def get_instance_control_sock(app_name, inventory_hostname, run_dir, stateboard=False):
    instance_fullname = get_instance_fullname(app_name, inventory_hostname, stateboard)
    return os.path.join(run_dir, '{}.control').format(instance_fullname)


def get_instance_conf_file(app_name, inventory_hostname, stateboard, conf_dir):
    instance_fullname = get_instance_fullname(app_name, inventory_hostname, stateboard)
    return os.path.join(conf_dir, '{}.yml').format(instance_fullname)


def get_app_conf_file(app_name, conf_dir):
    return os.path.join(conf_dir,'{}.yml').format(app_name)


def get_instance_conf_section(app_name, inventory_hostname, stateboard):
    return get_instance_fullname(app_name, inventory_hostname, stateboard)


def get_instance_work_dir(app_name, inventory_hostname, stateboard, data_dir):
    instance_fullname = get_instance_fullname(app_name, inventory_hostname, stateboard)
    return os.path.join(data_dir, '{}').format(instance_fullname)

def get_instance_run_dir(app_name, inventory_hostname, stateboard, run_dir):
    instance_fullname = get_instance_fullname(app_name, inventory_hostname, stateboard)
    return os.path.join(run_dir, '{}').format(instance_fullname)


def get_instance_systemd_service(app_name, inventory_hostname, stateboard):
    if stateboard:
        return '{}-stateboard'.format(app_name)
    return '{}@{}'.format(app_name, inventory_hostname)


def is_stateboard_on_machine(hosts, hostvars, inventory_hostname):
    machine_id = get_machine_identifier(hostvars[inventory_hostname])
    for i in hosts:
        if get_machine_identifier(hostvars[i]) == machine_id and 'stateboard' in hostvars[i] and hostvars[i]['stateboard'] == True:
            return True
    return False


def config_accept_vars(config, accept):
	return { k: v for k, v in config.items() if k.startswith(tuple(accept)) }


def config_reject_vars(config, reject):
	return { k: v for k, v in config.items() if not k.startswith(tuple(reject)) }


def get_sorted_instances_in_dc(instances, play_hosts):
    i = 0
    tmp = ''
    res = instances[:]
    for name in instances:
        if name in play_hosts:
            tmp = res[0]
            res[0] = name
            res[i] = tmp
        i = i + 1
    return sorted(res)

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
            'get_instance_run_dir': get_instance_run_dir,
            'is_stateboard_on_machine': is_stateboard_on_machine,
            'get_instances_on_machine': get_instances_on_machine,
            'accept_vars': config_accept_vars,
            'reject_vars': config_reject_vars,
            'get_sorted_instances_in_dc': get_sorted_instances_in_dc
        }
