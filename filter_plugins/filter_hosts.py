def one_not_expelled_instance_for_machine(hostvars, play_hosts):
    res = []
    added_machines = {}

    def get_machine_identifier(v):
        return v['ansible_host'] if 'ansible_host' in v else v['inventory_hostname']

    for i in play_hosts:
        if 'expelled' in hostvars[i] and hostvars[i]['expelled']:
            continue

        machine_id = get_machine_identifier(hostvars[i])
        if machine_id not in added_machines:
            added_machines[machine_id] = True
            res.append(i)

    return res


def one_not_expelled_instance(hostvars, play_hosts):
    for i in play_hosts:
        if 'expelled' in hostvars[i] and hostvars[i]['expelled']:
            continue

        return i

    raise Exception('At least one play host should be non-expelled')


class FilterModule(object):
    def filters(self):
        return {
            'one_not_expelled_instance_for_machine': one_not_expelled_instance_for_machine,
            'one_not_expelled_instance': one_not_expelled_instance,
        }
