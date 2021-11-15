import copy
import re
import sys
import unittest

import module_utils.helpers as helpers

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_validate_config import validate_config


def call_validate_config(module_hostvars, play_hosts=None):
    if play_hosts is None:
        play_hosts = module_hostvars.keys()

    return validate_config({
        'play_hosts': play_hosts,
        'module_hostvars': module_hostvars,
    })


class WrongTypeValue:
    pass


class TestValidateConfig(unittest.TestCase):
    def test_invalid_types(self):
        wrong_type_value = WrongTypeValue()

        params_by_types = {
            str: {
                'cartridge_scenario_name',
                'cartridge_app_user',
                'cartridge_app_group',
                'cartridge_app_install_dir',
                'cartridge_app_instances_dir',
                'cartridge_delivered_package_path',
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
                'cartridge_failover_params.etcd2_params.prefix',
                'cartridge_failover_params.etcd2_params.username',
                'cartridge_failover_params.etcd2_params.password',
                'cartridge_custom_steps_dir',
                'cartridge_conf_dir',
                'cartridge_run_dir',
                'cartridge_data_dir',
                'cartridge_memtx_dir_parent',
                'cartridge_vinyl_dir_parent',
                'cartridge_wal_dir_parent',
                'cartridge_systemd_dir',
                'cartridge_tmpfiles_dir',
                'zone',
                'cartridge_eval_body',
                'cartridge_eval_file',
                'allowed_members_states[0]',
                'cartridge_remote_backups_dir',
                'cartridge_fetch_backups_dir',
                'cartridge_restore_backup_path',
            },
            bool: {
                'cartridge_bootstrap_vshard',
                'cartridge_wait_buckets_discovery',
                'cartridge_failover',
                'restarted',
                'expelled',
                'all_rw',
                'cartridge_enable_tarantool_repo',
                'cartridge_auth.enabled',
                'cartridge_auth.users[0].deleted',
                'cartridge_multiversion',
                'cartridge_configure_systemd_unit_files',
                'cartridge_configure_tmpfiles',
                'cartridge_install_tarantool_for_tgz',
                'cartridge_remove_temporary_files',
                'cartridge_ignore_split_brain',
                'cartridge_failover_params.fencing_enabled',
                'edit_topology_allow_missed_instances',
                'allow_warning_issues',
                'show_issues',
                'cartridge_eval_with_retries',
                'cartridge_not_save_cookie_in_app_config',
                'cartridge_fetch_backups',
                'cartridge_force_restore',
                'cartridge_allow_alien_backup',
                'cartridge_skip_cleanup_on_restore',
            },
            dict: {
                'cartridge_defaults',
                'cartridge_runtime_params',
                'cartridge_app_config',
                'cartridge_failover_params',
                'cartridge_failover_params.stateboard_params',
                'cartridge_failover_params.etcd2_params',
                'cartridge_custom_scenarios',
                'cartridge_control_instance',
                'cartridge_extra_env',
            },
            int: {
                'bootstrap_vshard_retries',
                'bootstrap_vshard_delay',
                'connect_to_membership_retries',
                'connect_to_membership_delay',
                'instance_start_timeout',
                'instance_start_retries',
                'instance_start_delay',
                'instance_discover_buckets_timeout',
                'instance_discover_buckets_retries',
                'instance_discover_buckets_delay',
                'weight',
                'config.memtx_memory',
                'cartridge_auth.cookie_max_age',
                'cartridge_auth.cookie_renew_age',
                'cartridge_failover_params.etcd2_params.lock_delay',
                'cartridge_failover_params.failover_timeout',
                'cartridge_failover_params.fencing_timeout',
                'cartridge_failover_params.fencing_pause',
                'cartridge_keep_num_latest_dists',
                'twophase_netbox_call_timeout',
                'twophase_upload_config_timeout',
                'twophase_apply_config_timeout',
                'edit_topology_timeout',
                'edit_topology_healthy_timeout',
                'wait_members_alive_retries',
                'wait_members_alive_delay',
                'wait_cluster_has_no_issues_retries',
                'wait_cluster_has_no_issues_delay',
                'cartridge_eval_retries',
                'cartridge_eval_delay',
            },
            list: {
                'roles',
                'failover_priority',
                'cartridge_auth.users',
                'cartridge_failover_params.etcd2_params.endpoints',
                'cartridge_scenario',
                'cartridge_custom_steps',
                'cartridge_eval_args',
                'cartridge_paths_to_keep_on_cleanup',
                'cartridge_paths_to_keep_before_restore',
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

            if path.startswith('allowed_members_states[0]'):
                return {'allowed_members_states': [wrong_type_value]}

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

            if path.startswith('cartridge_failover_params.etcd2_params.endpoints[0]'):
                return {
                    'cartridge_failover_params': {
                        'etcd2_params': {
                            'endpoints': [wrong_type_value]
                        }
                    }
                }

            if path.startswith('cartridge_failover_params.etcd2_params.'):
                p = path.split('.')[-1]
                return {
                    'cartridge_failover_params': {
                        'etcd2_params': {
                            p: wrong_type_value
                        }
                    }
                }

            if path.startswith('cartridge_failover_params.'):
                p = path.split('.')[-1]
                return {'cartridge_failover_params': {p: wrong_type_value}}

            return {path: wrong_type_value}

        for t, params in params_by_types.items():
            for param in params:
                res = call_validate_config({'instance-1': get_wrong_params(param)})
                self.assertTrue(res.failed)
                self.assertIn("{} must be {}".format(param, t), res.msg)

    def test_instance_required_params(self):
        required_params = {
            'cartridge_app_name': 'app-name',
            'config': {'advertise_uri': 'localhost:3301'}
        }

        for p in required_params:
            params = required_params.copy()
            del params[p]

            res = call_validate_config({'instance-1': params})
            self.assertTrue(res.failed)
            self.assertIn("'{}' must be specified".format(p), res.msg)

    def test_config_required_params(self):
        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {}
            }
        })
        self.assertTrue(res.failed)
        self.assertIn("Missed required parameter 'advertise_uri' in 'instance-1' config", res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': '3301'}
            }
        })
        self.assertTrue(res.failed)
        self.assertIn("Instance advertise_uri must be specified as '<host>:<port>' ('instance-1')", res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'}
            }
        })
        self.assertFalse(res.failed, msg=res.msg)
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
            self.assertTrue(res.failed)
            self.assertIn(
                "Specified forbidden parameter '{}' in 'instance-1' config".format(p),
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
        self.assertTrue(res.failed)
        self.assertIn(
            "Cluster cookie must be specified in 'cartridge_cluster_cookie', not in 'cartridge_defaults'",
            res.msg
        )

    def test_instance_common_params(self):
        params = {
            'cartridge_app_name': ['app-name', 'other-app-name'],
            'cartridge_cluster_cookie': ['cookie', 'other-cookie'],
            'cartridge_not_save_cookie_in_app_config': [True, False],
            'cartridge_auth': [{'enabled': True}, {'enabled': False}],
            'cartridge_bootstrap_vshard': [True, False],
            'cartridge_failover': [True, False],
            'cartridge_app_config': [
                {'section-1': {'body': 'body'}},
                {'section-1': {'body': 'other-body'}}
            ],
            'cartridge_scenario': [
                ['task_1'],
                ['task_2'],
            ],
            'cartridge_custom_steps_dir': [
                'dir_1',
                'dir_2',
            ],
            'cartridge_custom_steps': [
                [{'name': 'task_1', 'file': 'task_1.yml'}],
                [{'name': 'task_2', 'file': 'task_2.yml'}],
            ],
            'cartridge_failover_promote_params': [
                {'replicaset_leaders': {'rpl-1': 'instance-2'}},
                {'replicaset_leaders': {'rpl-1': 'instance-3'}},
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
            self.assertTrue(res.failed)
            self.assertIn("'{}' must be the same for all hosts".format(p), res.msg)

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
                self.assertTrue(res.failed)
                self.assertIn("'{}' must be the same for all hosts".format(p), res.msg)

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
            self.assertTrue(res.failed)
            self.assertIn("Parameter '{}' is required for all replicasets".format(p), res.msg)

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
            self.assertTrue(res.failed)
            errmsg = "Replicaset parameters must be the same for all instances within one replicaset ('replicaset-1')"
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
                self.assertTrue(res.failed)
                errmsg = "Replicaset parameters must be the same for all instances within one replicaset " + \
                         "('replicaset-1')"
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
        self.assertTrue(res.failed)
        self.assertTrue(re.match(
            r"\.cartridge_app_config must be <(type|class) 'dict'>",
            res.msg,
        ), res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {},
            },
        })
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {'section-1': 42},
            },
        })
        self.assertTrue(res.failed)
        self.assertIn("'cartridge_app_config.section-1' must be dict", res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},
                'cartridge_app_config': {'section-1': {}},
            },
        })
        self.assertTrue(res.failed)
        self.assertIn(
            "'cartridge_app_config.section-1' must have 'body' or 'deleted' subsection",
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
        self.assertTrue(res.failed)
        self.assertIn(
            "cartridge_app_config.section-1' can contain only 'body' or 'deleted' subsections",
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
        self.assertTrue(res.failed)
        self.assertIn(
            "'cartridge_app_config.section-1' can contain only 'body' or 'deleted' subsections",
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
        self.assertTrue(res.failed)
        self.assertIn(
            "'cartridge_app_config.section-1' can contain only 'body' or 'deleted' subsections",
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
        self.assertTrue(res.failed)
        self.assertIn("'cartridge_app_config.section-1.deleted' must be bool", res.msg)

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
        self.assertTrue(res.failed)
        self.assertIn("'cartridge_app_config.section-1.body' is required", res.msg)

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
        self.assertFalse(res.failed, msg=res.msg)
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
        self.assertFalse(res.failed, msg=res.msg)
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
        self.assertFalse(res.failed, msg=res.msg)
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
        self.assertFalse(res.failed, msg=res.msg)
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
        self.assertFalse(res.failed, msg=res.msg)
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
        self.assertTrue(res.failed)
        self.assertIn(
            "Flags 'expelled' and 'restarted' cannot be set at the same time",
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
        self.assertTrue(res.failed)
        self.assertIn(
            "Only one of 'cartridge_failover' and 'cartridge_failover_params' can be specified",
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
        self.assertTrue(res.failed)
        self.assertIn(
            "Failover mode should be one of ['stateful', 'eventual', 'disabled']",
            res.msg
        )

        STATEFUL_FAILOVER_PARAMS = {
            'state_provider': 'stateboard',
            'stateboard_params': {},
            'etcd2_params': {},
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
            self.assertTrue(res.failed)
            self.assertIn(
                "'{}' failover parameter is allowed only for 'stateful' mode".format(p),
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
            self.assertTrue(res.failed)
            self.assertIn(
                "'{}' failover parameter is required for 'stateful' mode".format(p),
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
        self.assertTrue(res.failed)
        self.assertIn(
            "Stateful failover state provider should be one of ['stateboard', 'etcd2']",
            res.msg
        )

    def test_stateboard_provider(self):
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
        self.assertTrue(res.failed)
        self.assertIn(
            "stateboard_params' is required for 'stateboard' state provider",
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
            self.assertTrue(res.failed)
            self.assertIn(
                "stateboard_params.{}' is required for 'stateboard' provider".format(p),
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
        self.assertTrue(res.failed)
        self.assertIn(
            "Stateboard URI must be specified as '<host>:<port>'",
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
        self.assertTrue(res.failed)
        self.assertIn(
            'Stateboard password cannot contain symbols other than [a-zA-Z0-9_.~-]',
            res.msg
        )

    def test_etcd2_provider(self):
        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_failover_params': {
                    'mode': 'stateful',
                    'state_provider': 'etcd2',
                },
            },
        })
        self.assertFalse(res.failed)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_failover_params': {
                    'mode': 'stateful',
                    'state_provider': 'etcd2',
                    'etcd2_params': {
                        'prefix': '/',
                        'endpoints': [
                            'localhost:2379',
                            '2379',
                        ]
                    }
                },
            },
        })
        self.assertTrue(res.failed)
        self.assertIn(
            "etcd2 endpoints must be specified as '<host>:<port>'",
            res.msg
        )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_failover_params': {
                    'mode': 'stateful',
                    'state_provider': 'etcd2',
                    'etcd2_params': {
                        'prefix': '/',
                        'endpoints': [
                            'localhost:2379'
                        ]
                    }
                },
            },
        })
        self.assertFalse(res.failed)

    def test_custom_steps(self):
        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_scenario': ['task_1', 'task_2'],
                'cartridge_custom_steps_dir': './tasks',
                'cartridge_custom_steps': [
                    {'name': 'my_main', 'file': './tasks/main.yml'},
                ],
            },
        })
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_scenario': ['task_1', ['list']],
            },
        })
        self.assertTrue(res.failed)
        self.assertTrue(re.match(
            r"Incorrect type of task name '\['list']'. String expected, got: <(type|class) 'list'>",
            res.msg,
        ), res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_custom_steps_dir': './not_exists',
            },
        })
        self.assertTrue(res.failed)
        self.assertIn(
            "Directory './not_exists' from 'cartridge_custom_steps_dir' doesn't exists",
            res.msg
        )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_custom_steps': [
                    'test',
                ],
            },
        })
        self.assertTrue(res.failed)
        self.assertTrue(re.match(
            r"Incorrect type of custom task 'test'. Dictionary expected, got: <(type|class) 'str'>",
            res.msg,
        ), res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_custom_steps': [
                    {'name': ['qwerty']},
                ],
            },
        })
        self.assertTrue(res.failed)
        self.assertTrue(re.match(
            r"Incorrect type of name from task '{'name': \['qwerty']}'. String expected, got: <(type|class) 'list'>",
            res.msg,
        ), res.msg)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_custom_steps': [
                    {'name': 'task'},
                ],
            },
        })
        self.assertTrue(res.failed)
        self.assertIn(
            "No path to task file in custom task '{'name': 'task'}'",
            res.msg
        )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_custom_steps': [
                    {'name': 'task', 'file': ['qwerty']},
                ],
            },
        })
        self.assertTrue(res.failed)
        self.assertTrue(re.match(
            r"Incorrect type of file path from task '{'name': 'task', 'file': \['qwerty']}'. "
            r"String expected, got: <(type|class) 'list'>",
            res.msg,
        ))

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_custom_steps': [
                    {'name': 'task', 'file': 'qwerty'},
                ],
            },
        })
        self.assertTrue(res.failed)
        self.assertIn(
            "File 'qwerty' from custom task '{'name': 'task', 'file': 'qwerty'}' doesn't exists",
            res.msg
        )

    def test_failover_promote_params(self):
        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_failover_promote_params': {
                    'replicaset_leaders': {'rpl-1': 'instance-2'},
                    'force_inconsistency': False,
                },
            },
        })
        self.assertFalse(res.failed)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_failover_promote_params': {
                    'replicaset_leaders': {'rpl-1': 'instance-2'},
                },
            },
        })
        self.assertFalse(res.failed)

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_failover_promote_params': {
                    'replicaset_leaders': {'rpl-1': 'instance-2'},
                    'force_inconsistency': False,
                    'bad-field': 'I am very very bad',
                },
            },
        })
        self.assertTrue(res.failed)
        self.assertIn(
            "Passed unknown failover promote parameter: 'bad-field'",
            res.msg
        )

        res = call_validate_config({
            'instance-1': {
                'cartridge_app_name': 'app-name',
                'cartridge_cluster_cookie': 'cookie',
                'config': {'advertise_uri': 'localhost:3301'},

                'cartridge_failover_promote_params': {
                    'replicaset_leaders': {'rpl-1': 43},
                    'force_inconsistency': False,
                },
            },
        })
        self.assertTrue(res.failed)
        self.assertIn(
            "Variable 'replicaset_leaders' should be of type map(string -> string)",
            res.msg
        )


if __name__ == '__main__':
    unittest.main()
