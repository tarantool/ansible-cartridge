#!/usr/bin/python

class FilterModule:
    def delete_by_key(self, d, key):
        return { k: v for k, v in d.items() if k != key }

    def filters(self):
        return {
            'delete_by_key': self.delete_by_key,
        }
