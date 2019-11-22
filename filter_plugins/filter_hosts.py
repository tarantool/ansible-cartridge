def one_not_expelled_instance_for_machine(hostvars, play_hosts):
    res = []
    added_machines = {}

    for i in play_hosts:
        if 'expelled' in hostvars[i] and hostvars[i]['expelled']:
            continue

        machine_id = hostvars[i]['ansible_machine_id']
        if machine_id not in added_machines:
            added_machines[machine_id] = True
            res.append(i)

    return res


class FilterModule(object):
    def filters(self):
        return {
            'one_not_expelled_instance_for_machine': one_not_expelled_instance_for_machine,
        }
