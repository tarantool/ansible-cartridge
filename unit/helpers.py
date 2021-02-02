def add_replicaset(instance, alias, roles, servers,
                   status='healthy', all_rw=False, weight=None, vshard_group=None):
    r_uuid = '{}-uuid'.format(alias)
    r_servers = []
    for s in servers:  # servers = ['alias-1', 'alias-2']
        r_servers.append({
            'alias': s,
            'uuid': '{}-uuid'.format(s),
            'uri': '{}-uri'.format(s),
            'status': 'healthy',
            'replicaset': {
                'uuid': r_uuid,
                'alias': alias,
                'roles': roles,
            }
        })

    instance.add_topology_servers(r_servers)

    replicaset = {
        'uuid': r_uuid,
        'alias': alias,
        'status': status,
        'roles': roles,
        'weight': weight,
        'all_rw': all_rw,
        'vshard_group': vshard_group,
        'servers': [{'alias': s, 'priority': i + 1} for i, s in enumerate(servers)]
    }
    instance.add_topology_replicaset(replicaset)

    return replicaset


def set_box_cfg(instance, **kwargs):
    instance.set_box_cfg(kwargs)
