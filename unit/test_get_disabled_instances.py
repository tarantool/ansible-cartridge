import sys
import unittest

import module_utils.helpers as helpers

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_get_disabled_instances import count_disabled_instances


def call_count_disabled_instances(
    instances_info,
    play_hosts=None,
    ignore_split_brain=False,
):
    module_hostvars = {
        instance_name: {
            'instance_info': {
                'disabled_instances': instance_info['disabled_instances'],
                'topology_checksum': instance_info.get('checksum', 1234567890),
            },
            'disabled': instance_info.get('disabled', False),
        }
        for instance_name, instance_info
        in instances_info.items()
    }
    if play_hosts is None:
        play_hosts = module_hostvars.keys()

    return count_disabled_instances({
        'module_hostvars': module_hostvars,
        'play_hosts': play_hosts,
        'ignore_split_brain': ignore_split_brain,
    })


class TestCountDisabledInstances(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_count_disabled_instances(self):
        # Healthy cluster

        helpers.WARNINGS = []
        res = call_count_disabled_instances({
            'instance-1': {'disabled_instances': []},
            'instance-2': {'disabled_instances': []},
            'instance-3': {'disabled_instances': []},
        })
        self.assertFalse(res.failed)
        self.assertEqual(res.kwargs['cluster'], [])
        self.assertEqual(res.kwargs['inventory'], [])
        self.assertEqual(helpers.WARNINGS, [])

        helpers.WARNINGS = []
        res = call_count_disabled_instances({
            'instance-1': {'disabled_instances': ['instance-2', 'instance-3'], 'checksum': 2},
            'instance-2': {'disabled_instances': [], 'checksum': 1, 'disabled': True},
            'instance-3': {'disabled_instances': [], 'checksum': 1},
        })
        self.assertFalse(res.failed)
        self.assertEqual(res.kwargs['cluster'], ['instance-2', 'instance-3'])
        self.assertEqual(res.kwargs['inventory'], ['instance-2'])
        self.assertEqual(helpers.WARNINGS, [])

        helpers.WARNINGS = []
        res = call_count_disabled_instances({
            'instance-1': {'disabled_instances': None, 'checksum': None, 'disabled': True},
            'instance-2': {'disabled_instances': [], 'checksum': 1},
            'instance-3': {'disabled_instances': ['instance-2'], 'checksum': 2},
        })
        self.assertFalse(res.failed)
        self.assertEqual(res.kwargs['cluster'], ['instance-2'])
        self.assertEqual(res.kwargs['inventory'], ['instance-1'])
        self.assertEqual(helpers.WARNINGS, [])

        # Split brain

        res = call_count_disabled_instances({
            'instance-1': {'disabled_instances': ['instance-2', 'instance-3'], 'disabled': True},
            'instance-2': {'disabled_instances': []},
            'instance-3': {'disabled_instances': []},
        }, ignore_split_brain=False)
        self.assertTrue(res.failed)
        self.assertEqual(
            res.msg,
            "It seems that you have split brain in your cluster. "
            "Set 'cartridge_ignore_split_brain' flag to ignore this error."
        )

        helpers.WARNINGS = []
        res = call_count_disabled_instances({
            'instance-1': {'disabled_instances': ['instance-2', 'instance-3'], 'disabled': True},
            'instance-2': {'disabled_instances': []},
            'instance-3': {'disabled_instances': []},
        }, ignore_split_brain=True)
        self.assertFalse(res.failed)
        self.assertEqual(res.kwargs['cluster'], [])
        self.assertEqual(res.kwargs['inventory'], ['instance-1'])
        self.assertEqual(helpers.WARNINGS, ["It seems that you have split brain in your cluster."])

        helpers.WARNINGS = []
        res = call_count_disabled_instances({
            'instance-1': {'disabled_instances': ['instance-2', 'instance-3'], 'disabled': True},
            'instance-2': {'disabled_instances': ['instance-1']},
            'instance-3': {'disabled_instances': ['instance-1']},
        }, ignore_split_brain=True)
        self.assertFalse(res.failed)
        self.assertEqual(res.kwargs['cluster'], ['instance-1'])
        self.assertEqual(res.kwargs['inventory'], ['instance-1'])
        self.assertEqual(helpers.WARNINGS, ["It seems that you have split brain in your cluster."])

        helpers.WARNINGS = []
        res = call_count_disabled_instances({
            'instance-1': {'disabled_instances': ['instance-3', 'instance-4']},
            'instance-2': {'disabled_instances': ['instance-3', 'instance-4']},
            'instance-3': {'disabled_instances': ['instance-1', 'instance-2']},
            'instance-4': {'disabled_instances': ['instance-1', 'instance-2']},
        }, ignore_split_brain=True)
        self.assertFalse(res.failed)
        self.assertEqual(res.kwargs['cluster'], ['instance-1', 'instance-2', 'instance-3', 'instance-4'])
        self.assertEqual(res.kwargs['inventory'], [])
        self.assertEqual(helpers.WARNINGS, ["It seems that you have split brain in your cluster."])

        # No correct topology config

        res = call_count_disabled_instances({
            'instance-1': {'disabled_instances': None, 'checksum': None},
            'instance-2': {'disabled_instances': [], 'checksum': 1},
            'instance-3': {'disabled_instances': [], 'checksum': 2},
        })
        self.assertTrue(res.failed)
        self.assertEqual(res.msg, 'All instances in cluster has different topology configs')
