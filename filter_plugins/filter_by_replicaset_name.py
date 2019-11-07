#!/usr/bin/python

class FilterModule:
    def instances_by_replicaset_name(self, d, replicaset_name):
        return [
            v['inventory_hostname'] for k, v in d.items()
            if 'replicaset_name' in v and v['replicaset_name'] == replicaset_name
        ]

    def filters(self):
        return {
            'instances_by_replicaset_name': self.instances_by_replicaset_name,
        }
