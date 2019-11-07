#!/usr/bin/python

class FilterModule:
    def filter_by_replicaset_name(self, d, replicaset_name):
        return {
            k: v for k, v in d.items()
            if 'replicaset_name' in v and v['replicaset_name'] == replicaset_name
        }

    def filters(self):
        return {
            'filter_by_replicaset_name': self.filter_by_replicaset_name,
        }
