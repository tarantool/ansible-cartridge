def cartridge_hosts(hostvars):
    return [
        v['inventory_hostname']
        for _, v in hostvars.items()
        if 'cartridge_cluster_cookie' in v
    ]


class FilterModule(object):
    def filters(self):
        return {
            'cartridge_hosts': cartridge_hosts,
        }
