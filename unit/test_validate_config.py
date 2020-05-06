# Hack ansible.module_utils.helpers import
import sys
import copy
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


class WrongTypeValue:
    pass


class TestValidateConfig(unittest.TestCase):
    def test_invalid_types(self):
        wrong_type_value = WrongTypeValue()

        params_by_types = {
            str: {
                'cartridge_package_path',
                'cartridge_app_name',
                'cartridge_cluster_cookie',
                'replicaset_alias',
                'vshard_group',
                'config.advertise_uri',
                'cartridge_auth.users[0].username',
                'cartridge_auth.users[0].password',
                'cartridge_auth.users[0].fullname',
                'cartridge_auth.users[0].email',
                'roles[0]',
                'failover_priority[0]',
                'cartridge_failover_params.mode',
                'cartridge_failover_params.state_provider',
                'cartridge_failover_params.stateboard_params.uri',
                'cartridge_failover_params.stateboard_params.password',
            },
            bool: {
                'cartridge_bootstrap_vshard',
                'cartridge_failover',
                'restarted',
                'expelled',
                'all_rw',
                'cartridge_enable_tarantool_repo',
                'cartridge_auth.enabled',
                'cartridge_auth.users[0].deleted',
            },
            dict: {
                'cartridge_defaults',
                'cartridge_app_config',
                'cartridge_failover_params',
                'cartridge_failover_params.stateboard_params',
            },
            int: {
                'instance_start_timeout',
                'weight',
                'config.memtx_memory',
                'cartridge_auth.cookie_max_age',
                'cartridge_auth.cookie_renew_age',
            },
            list: {
                'roles',
                'failover_priority',
                'cartridge_auth.users',
            }
        }

        def get_wrong_params(path):
            if path.startswith('config.'):
                p = path.split('.')[-1]
                return {'config': {p: wrong_type_value}}

            if path.startswith('roles[0]'):
                return {'roles': [wrong_type_value]}

            if path.startswith('failover_priority[0]'):
                return {'failover_priority': [wrong_type_value]}

            if path.startswith('cartridge_auth.users[0].'):
                p = path.split('.')[-1]
                return {
                    'cartridge_auth': {
                        'users': [{p: wrong_type_value}]
                    }
                }

            if path.startswith('cartridge_auth.'):
                p = path.split('.')[-1]
                return {'cartridge_auth': {p: wrong_type_value}}

            if path.startswith('cartridge_failover_params.stateboard_params.'):
                p = path.split('.')[-1]
                return {
                    'cartridge_failover_params': {
                        'stateboard_params': {
                            p: wrong_type_value
                        }
                    }
                }

            if path.startswith('cartridge_failover_params.'):
                p = path.split('.')[-1]
                return {'cartridge_failover_params': {p: wrong_type_value}}

            return {path: wrong_type_value}

        for t, params in params_by_types.items():
            for p in params:
                res = call_validate_config({'instance-1': get_wrong_params(p)})
                self.assertFalse(res.success)
                self.assertIn("{} must be {}".format(p, t), res.msg)

    def test_instance_required_params(self):
        required_params = {
            'cartridge_app_name': 'app-name',
            'cartridge_cluster_cookie': 'cookie',
            'config': {'advertise_uri': 'localhost:3301'}
        }

        for p in required_params:
            params = required_params.copy()
            del params[p]

            res = call_validate_config({'instance-1': params})
            self.assertFalse(res.success)
            self.assertIn('"{}" must be specified'.format(p), res.msg)

    def test_config_required_params(self):
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
        self.assertIn('Instance advertise_uri must be specified as "<host>:<port>" ("instance-1")', res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'}
            }
        })
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

    def test_forbidden_params(self):
        params = {
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'}
            }
        }

        for p in ['alias', 'console_sock', 'pid_file', 'workdir', 'cluster_cookie']:
            bad_params = copy.deepcopy(params)
            bad_params['instance-1']['config'][p] = 'I AM FORBIDDEN'

            res = call_validate_config(bad_params)
            self.assertFalse(res.success)
            self.assertIn(
                'Specified forbidden parameter "{}" in "instance-1" config'.format(p),
                res.msg
            )

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
            'Cluster cookie must be specified in "cartridge_cluster_cookie", not in "cartridge_defaults"',
            res.msg
        )

    def test_instance_common_params(self):
        params = {
            'cartridge_app_name': ['app-name', 'other-app-name'],
            'cartridge_cluster_cookie': ['cookie', 'other-cookie'],
            'cartridge_auth': [{'enabled': True}, {'enabled': False}],
            'cartridge_bootstrap_vshard': [True, False],
            'cartridge_failover': [True, False],
            'cartridge_app_config': [
                {'section-1': {'body': 'body'}},
                {'section-1': {'body': 'other-body'}}
            ],
        }

        required_params = {
            'cartridge_app_name': 'app-name',
            'cartridge_cluster_cookie': 'cookie',
            'config': {'advertise_uri': 'localhost:3301'},
        }

        for p, values in params.items():
            v1, v2 = values

            # passed different values
            instance1_params = copy.deepcopy(required_params)
            instance1_params.update({p: v1})

            instance2_params = copy.deepcopy(required_params)
            instance2_params.update({p: v2})

            res = call_validate_config({
                'instance-1': instance1_params,
                'instance-2': instance2_params,
            })
            self.assertFalse(res.success)
            self.assertIn('"{}" must be the same for all hosts'.format(p), res.msg)

            # passed only for one instance
            if p not in required_params:
                instance1_params = copy.deepcopy(required_params)
                instance1_params.update({p: v1})

                instance2_params = copy.deepcopy(required_params)
                # don't set for instance-2

                res = call_validate_config({
                    'instance-1': instance1_params,
                    'instance-2': instance2_params,
                })
                self.assertFalse(res.success)
                self.assertIn('"{}" must be the same for all hosts'.format(p), res.msg)

    def test_replicaset_required_params(self):
        instance_required_params = {
            'cartridge_app_name': 'app-name',
            'cartridge_cluster_cookie': 'cookie',
            'config': {'advertise_uri': 'localhost:3301'},
            'replicaset_alias': 'replicaset-1',
            'failover_priority': ['instance-1'],
            'roles': ['role-1'],
        }

        replicaset_required_params = ['roles']

        for p in replicaset_required_params:
            params = copy.deepcopy(instance_required_params)
            del params[p]

            res = call_validate_config({'instance-1': params})
            self.assertFalse(res.success)
            self.assertIn('Parameter "{}" is required for all replicasets'.format(p), res.msg)

    def test_replicaset_common_params(self):
        params = {
            'failover_priority': [['i1', 'i2'], ['i2', 'i1']],
            'roles': [['role-1', 'role-2'], ['role-2', 'role-1']],
            'all_rw': [True, False],
            'weight': [1, 2],
            'vshard_group': ['hot', 'cold'],
        }

        replicaset1_required_params = {  # instance-11, instance-12
            'cartridge_app_name': 'app-name',
            'cartridge_cluster_cookie': 'cookie',
            'config': {'advertise_uri': 'localhost:3301'},

            'replicaset_alias': 'replicaset-1',
            'failover_priority': ['instance-11'],
            'roles': ['role-1'],
        }

        replicaset2_params = {  # instance-21
            'cartridge_app_name': 'app-name',
            'cartridge_cluster_cookie': 'cookie',
            'config': {'advertise_uri': 'localhost:3302'},

            'replicaset_alias': 'replicaset-2',
            'failover_priority': ['instance-21'],
            'roles': ['role-2'],
        }

        for p, values in params.items():
            v1, v2 = values

            # passed different values
            instance11_params = copy.deepcopy(replicaset1_required_params)
            instance11_params.update({p: v1})

            instance12_params = copy.deepcopy(replicaset1_required_params)
            instance12_params.update({p: v2})

            res = call_validate_config({
                'instance-11': instance11_params,
                'instance-12': instance12_params,
                'instance-21': replicaset2_params,
            })
            self.assertFalse(res.success)
            errmsg = 'Replicaset parameters must be the same for all instances within one replicaset ("replicaset-1")'
            self.assertIn(errmsg, res.msg)

            # passed only for one instance
            if p not in replicaset1_required_params:
                instance11_params = copy.deepcopy(replicaset1_required_params)
                instance11_params.update({p: v1})

                instance12_params = copy.deepcopy(replicaset1_required_params)
                # don't set for instance-12

                res = call_validate_config({
                    'instance-11': instance11_params,
                    'instance-12': instance12_params,
                    'instance-21': replicaset2_params,
                })
                self.assertFalse(res.success)
                errmsg = 'Replicaset parameters must be the same for all instances within one replicaset ' + \
                    '("replicaset-1")'
                self.assertIn(errmsg, res.msg)

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
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {'section-1': 42},
            },
        })
        self.assertFalse(res.success)
        self.assertIn('"cartridge_app_config.section-1" must be dict', res.msg)

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
            '"cartridge_app_config.section-1" must have "body" or "deleted" subsection',
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
            'cartridge_app_config.section-1" can contain only "body" or "deleted" subsections',
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
            '"cartridge_app_config.section-1" can contain only "body" or "deleted" subsections',
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
            '"cartridge_app_config.section-1" can contain only "body" or "deleted" subsections',
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
        self.assertIn('"cartridge_app_config.section-1.deleted" must be bool', res.msg)

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
        self.assertIn('"cartridge_app_config.section-1.body" is required', res.msg)

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
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

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
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

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
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

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
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        # expelled
        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'expelled': True,
            },
        })
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

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
            'Flags "expelled" and "restarted" cannot be set at the same time',
            res.msg
        )

    def test_failover(self):
        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_failover_params': {
                    'mode': 'disabled'
                },
                'cartridge_failover': True,
            },
        })
        self.assertFalse(res.success)
        self.assertIn(
            'Only one of "cartridge_failover" and "cartridge_failover_params" can be specified',
            res.msg
        )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_failover_params': {
                    'mode': 'invalid',
                },
            },
        })
        self.assertFalse(res.success)
        self.assertIn(
            "Failover mode should be one of ['stateful', 'eventual', 'disabled']",
            res.msg
        )

        STATEFUL_FAILOVER_PARAMS = {
            'state_provider': 'stateboard',
            'stateboard_params': {},
        }

        for p, value in STATEFUL_FAILOVER_PARAMS.items():
            params = {
                'instance-1': {
                    'cartridge_app_name': 'app-name',
                    'cartridge_cluster_cookie': 'cookie',
                    'config': {'advertise_uri': 'localhost:3301'},

                    'cartridge_failover_params': {
                        'mode': 'eventual',
                    },
                }
            }

            params['instance-1']['cartridge_failover_params'].update({
                p: value
            })

            res = call_validate_config(params)
            self.assertFalse(res.success)
            self.assertIn(
                '"{}" failover parameter is allowed only for "stateful" mode'.format(p),
                res.msg
            )

        STATEFUL_FAILOVER_REQUIRED_PARAMS = [
            'state_provider',
        ]

        for p in STATEFUL_FAILOVER_REQUIRED_PARAMS:
            params = {
                'instance-1': {
                    'cartridge_app_name': 'app-name',
                    'cartridge_cluster_cookie': 'cookie',
                    'config': {'advertise_uri': 'localhost:3301'},

                    'cartridge_failover_params': {
                        'mode': 'stateful',
                        'state_provider': 'stateboard',
                    },
                }
            }

            del params['instance-1']['cartridge_failover_params'][p]

            res = call_validate_config(params)
            self.assertFalse(res.success)
            self.assertIn(
                '"{}" failover parameter is required for "stateful" mode'.format(p),
                res.msg
            )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_failover_params': {
                    'mode': 'stateful',
                    'state_provider': 'invalid',
                },
            },
        })
        self.assertFalse(res.success)
        self.assertIn(
            "Stateful failover state provider should be one of ['stateboard']",
            res.msg
        )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_failover_params': {
                    'mode': 'stateful',
                    'state_provider': 'stateboard',
                },
            },
        })
        self.assertFalse(res.success)
        self.assertIn(
            'stateboard_params" is required for "stateboard" state provider',
            res.msg
        )

        STATEBOARD_PROVIDER_REQUIRED_PARAMS = [
            'uri',
            'password',
        ]

        for p in STATEBOARD_PROVIDER_REQUIRED_PARAMS:
            params = {
                'instance-1': {
                    'cartridge_app_name': 'app-name',
                    'cartridge_cluster_cookie': 'cookie',
                    'config': {'advertise_uri': 'localhost:3301'},

                    'cartridge_failover_params': {
                        'mode': 'stateful',
                        'state_provider': 'stateboard',
                        'stateboard_params': {
                            'uri': 'localhost:3310',
                            'password': 'passwd',
                        }
                    },
                },
            }

            del params['instance-1']['cartridge_failover_params']['stateboard_params'][p]

            res = call_validate_config(params)
            self.assertFalse(res.success)
            self.assertIn(
                'stateboard_params.{}" is required for "stateboard" provider'.format(p),
                res.msg
            )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_failover_params': {
                    'mode': 'stateful',
                    'state_provider': 'stateboard',
                    'stateboard_params': {
                        'uri': '3301',
                        'password': 'passwd',
                    }
                },
            },
        })
        self.assertFalse(res.success)
        self.assertIn(
            'Stateboard URI must be specified as "<host>:<port>"',
            res.msg
        )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_failover_params': {
                    'mode': 'stateful',
                    'state_provider': 'stateboard',
                    'stateboard_params': {
                        'uri': 'localhost:3301',
                        'password': '@@@passwd',
                    }
                },
            },
        })
        self.assertFalse(res.success)
        self.assertIn(
            'Stateboard password cannot contain symbols other than [a-zA-Z0-9_.~-]',
            res.msg
        )


if __name__ == '__main__':
    unittest.main()
