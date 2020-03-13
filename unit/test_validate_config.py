# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import unittest

from library.cartridge_validate_config import validate_config


def call_validate_config(hostvars, play_hosts=None):
    if play_hosts is None:
        play_hosts = hostvars.keys()

    return validate_config({
        'hosts': play_hosts,
        'hostvars': hostvars,
    })


class TestValidateConfig(unittest.TestCase):
    def test_required_params(self):
        res = call_validate_config({'instance-1': {}})
        self.assertFalse(res.success)
        self.assertIn('`cartridge_app_name` must be specified', res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
            }
        })
        self.assertFalse(res.success)
        self.assertIn('`cartridge_cluster_cookie` must be specified', res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
            }
        })
        self.assertFalse(res.success)
        self.assertIn('Missed required parameter `config` for "instance-1"', res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {}
            }
        })
        self.assertFalse(res.success)
        self.assertIn('Missed required parameter "advertise_uri" in "instance-1" config', res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': '3301'}
            }
        })
        self.assertFalse(res.success)
        self.assertIn('Instance advertise_uri must be specified as `<host>:<port>` ("instance-1")', res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'}
            }
        })
        self.assertTrue(res.success)

    def test_forbidden_params(self):
        config = {
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'}
            }
        }

        for p in ['alias', 'console_sock', 'pid_file', 'workdir', 'cluster_cookie']:
            config['instance-1']['config'][p] = 'I AM FORBIDDEN'

            res = call_validate_config(config)
            self.assertFalse(res.success)
            self.assertIn(
                'Specified forbidden parameter "{}" in "instance-1" config'.format(p),
                res.msg
            )

            del config['instance-1']['config'][p]

    def test_cluster_cookie(self):
        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'cartridge_defaults': {'cluster_cookie': 'cookie'},
                'config': {'advertise_uri': 'localhost:3301'}
            }
        })
        self.assertFalse(res.success)
        self.assertIn(
            'Cluster cookie must be specified in `cartridge_cluster_cookie`, not in `cartridge_defaults`',
            res.msg
        )

    def test_invalid_types(self):
        res = call_validate_config({
            'instance-1': {
                'cartridge_package_path': 42
            }
        })
        self.assertFalse(res.success)
        self.assertIn("cartridge_package_path must be <class 'str'>", res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_failover': 42
            }
        })
        self.assertFalse(res.success)
        self.assertIn("cartridge_failover must be <class 'bool'>", res.msg)

        res = call_validate_config({
            'instance-1': {
                'config': 42
            }
        })
        self.assertFalse(res.success)
        self.assertIn("config must be <class 'dict'>", res.msg)

        res = call_validate_config({
            'instance-1': {
                'config': {
                    'advertise_uri': 42,
                }
            }
        })
        self.assertFalse(res.success)
        self.assertIn("advertise_uri must be <class 'str'>", res.msg)

        res = call_validate_config({
            'instance-1': {
                'config': {
                    'memtx_memory': 'some-string'
                }
            }
        })
        self.assertFalse(res.success)
        self.assertIn("memtx_memory must be <class 'int'>", res.msg)

        res = call_validate_config({
            'instance-1': {
                'restarted': 'yes',
            }
        })
        self.assertFalse(res.success)
        self.assertIn("restarted must be <class 'bool'>", res.msg)

        res = call_validate_config({
            'instance-1': {
                'expelled': 'yes',
            }
        })
        self.assertFalse(res.success)
        self.assertIn("expelled must be <class 'bool'>", res.msg)

    def test_common_params_are_the_same(self):
        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
            },
            'instance-2': {
                'cartridge_app_name': 'other-app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3302'},
            },
        })
        self.assertFalse(res.success)
        self.assertIn("`cartridge_app_name` must be the same for all hosts", res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
            },
            'instance-2': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'other-cookie',
                'config': {'advertise_uri': 'localhost:3302'},
            },
        })
        self.assertFalse(res.success)
        self.assertIn("Cluster cookie must be the same for all instances", res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {
                    'section-1': {'body': 42}
                },
            },
            'instance-2': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3302'},
                'cartridge_app_config': {
                    'section-1': {'body': 420}
                },
            },
        })
        self.assertFalse(res.success)
        self.assertIn("`cartridge_app_config` must be the same for all hosts", res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_failover': True,
            },
            'instance-2': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3302'},
                'cartridge_failover': False,
            },
        })
        self.assertFalse(res.success)
        self.assertIn("`cartridge_failover` must be the same for all hosts", res.msg)

    def test_replicasets(self):
        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'replicaset_alias': 'replicaset-1',
                'failover_priority': ['instance-1', 'instance-2'],
            },
        })
        self.assertFalse(res.success)
        self.assertIn('Parameter "roles" is required for all replicasets', res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'replicaset_alias': 'replicaset-1',
                'roles': ['I-am-role'],
            },
        })
        self.assertFalse(res.success)
        self.assertIn('Parameter "failover_priority" is required for all replicasets', res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'replicaset_alias': 'replicaset-1',
                'failover_priority': ['instance-1', 'instance-2'],
                'roles': 'I-am-role',
            },
        })
        self.assertFalse(res.success)
        self.assertIn("roles must be <class 'list'>", res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'replicaset_alias': 'replicaset-1',
                'failover_priority': ['instance-1', 'instance-2'],
                'roles': ['I-am-role'],
            },
        })
        self.assertTrue(res.success)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'replicaset_alias': 'replicaset-1',
                'failover_priority': ['instance-1', 'instance-2'],
                'roles': ['I-am-role'],
            },
            'instance-2': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3302'},
                'replicaset_alias': 'replicaset-1',
                'failover_priority': ['instance-1', 'instance-2'],
                'roles': ['I-am-another-role'],
            },
        })
        self.assertFalse(res.success)
        self.assertIn(
            "Replicaset parameters must be the same for all instances with the same `replicaset_alias`",
            res.msg
        )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'replicaset_alias': 'replicaset-1',
                'failover_priority': ['instance-1', 'instance-2'],
                'roles': ['I-am-role'],
            },
            'instance-2': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3302'},
                'replicaset_alias': 'replicaset-1',
                'failover_priority': ['instance-2', 'instance-1'],
                'roles': ['I-am-role'],
            },
        })
        self.assertFalse(res.success)
        self.assertIn(
            "Replicaset parameters must be the same for all instances with the same `replicaset_alias`",
            res.msg
        )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'replicaset_alias': 'replicaset-1',
                'roles': ['I-am-role'],
                'failover_priority': ['instance-1', 'instance-2'],
                'vshard_group': 'group1',
            },
            'instance-2': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3302'},
                'replicaset_alias': 'replicaset-1',
                'roles': ['I-am-role'],
                'failover_priority': ['instance-1', 'instance-2'],
                'vshard_group': 'group1',
            },
        })
        self.assertTrue(res.success)

    def test_app_config(self):
        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': 42,
            },
        })
        self.assertFalse(res.success)
        self.assertIn("cartridge_app_config must be <class 'dict'>", res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {},
            },
        })
        self.assertTrue(res.success)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {'section-1': 42},
            },
        })
        self.assertFalse(res.success)
        self.assertIn("`cartridge_app_config.section-1` must be dict", res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {'section-1': {}},
            },
        })
        self.assertFalse(res.success)
        self.assertIn(
            "`cartridge_app_config.section-1` must have `body` or `deleted` subsection",
            res.msg
        )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {
                    'section-1': {'wrong-key': 42}
                },
            },
        })
        self.assertFalse(res.success)
        self.assertIn(
            "`cartridge_app_config.section-1` can contain only `body` or `deleted` subsections",
            res.msg
        )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {
                    'section-1': {'wrong-key': 42}
                },
            },
        })
        self.assertFalse(res.success)
        self.assertIn(
            "`cartridge_app_config.section-1` can contain only `body` or `deleted` subsections",
            res.msg
        )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {
                    'section-1': {
                        'wrong-key': 42,
                        'body': 42,
                    }
                },
            },
        })
        self.assertFalse(res.success)
        self.assertIn(
            "`cartridge_app_config.section-1` can contain only `body` or `deleted` subsections",
            res.msg
        )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {
                    'section-1': {
                        'body': 42,
                        'deleted': 42,
                    }
                },
            },
        })
        self.assertFalse(res.success)
        self.assertIn("`cartridge_app_config.section-1.deleted` must be bool", res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {
                    'section-1': {'deleted': False}
                },
            },
        })
        self.assertFalse(res.success)
        self.assertIn("`cartridge_app_config.section-1.body` is required", res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {
                    'section-1': {'body': 42}
                },
            },
        })
        self.assertTrue(res.success)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {
                    'section-1': {
                        'body': 42,
                        'deleted': True,
                    }
                },
            },
        })
        self.assertTrue(res.success)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {
                    'section-1': {'deleted': True}
                },
            },
        })
        self.assertTrue(res.success)

    def test_instance_states(self):
        # restarted
        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'restarted': True,
            },
        })
        self.assertTrue(res.success)

        # expelled
        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'expelled': True,
            },
        })
        self.assertTrue(res.success)

        # both expelled and restarted set to true
        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'expelled': True,
                'restarted': True,
            },
        })
        self.assertFalse(res.success)
        self.assertIn(
            'Flags "expelled" and "restarted" can not be set at the same time',
            res.msg
        )


if __name__ == '__main__':
    unittest.main()
