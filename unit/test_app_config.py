# Hack ansible.module_utils.helpers import
import sys
import module_utils.helpers as helpers
sys.modules['ansible.module_utils.helpers'] = helpers

import os
sys.path.append(os.path.dirname(__file__))

import unittest
from instance import Instance

from library.cartridge_app_config import config_app


def call_config_app(control_sock, config):
    return config_app({
        'control_sock': control_sock,
        'app_config': config,
    })


class TestAppConfig(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_empty_config(self):
        res = call_config_app(self.console_sock, {})
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

    def test_edit_system_sections(self):
        system_sections = [
            'topology',
            'vshard',
            'vshard_groups',
            'auth',
            'users_acl',
        ]
        for section in system_sections:
            self.instance.clear_calls('config_patch_clusterwide')

            res = call_config_app(self.console_sock, {
                section: {}
            })
            self.assertFalse(res.success)
            self.assertIn('Unable to patch config system section', res.msg)

            calls = self.instance.get_calls('config_patch_clusterwide')
            self.assertEqual(len(calls), 0)

    def test_adding_new_sections(self):
        SECTION_NAME = 'new-section'
        SECTION_BODY = 'SECTION BODY'

        # config is empty
        self.instance.set_variable('config', {})
        self.instance.clear_calls('config_patch_clusterwide')

        res = call_config_app(self.console_sock, {
            SECTION_NAME: {
                'body': SECTION_BODY,
            }
        })
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('config_patch_clusterwide')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            SECTION_NAME: SECTION_BODY
        })

        # config is already set (res.changed should be false)
        self.instance.set_variable('config', {
            SECTION_NAME: SECTION_BODY
        })
        self.instance.clear_calls('config_patch_clusterwide')

        res = call_config_app(self.console_sock, {
            SECTION_NAME: {
                'body': SECTION_BODY,
            }
        })
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('config_patch_clusterwide')
        self.assertEqual(len(calls), 0)

    def test_deleting_sections(self):
        SECTION1_NAME = 'section-1'
        SECTION1_BODY = 'SECTION-1 BODY'
        SECTION2_NAME = 'section-2'
        SECTION2_BODY = 'SECTION-2 BODY'

        # set two sections
        self.instance.set_variable('config', {
            SECTION1_NAME: SECTION1_BODY,
            SECTION2_NAME: SECTION2_BODY,
        })
        self.instance.clear_calls('config_patch_clusterwide')

        # delete section-1
        res = call_config_app(self.console_sock, {
            SECTION1_NAME: {
                'deleted': True,
            }
        })
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('config_patch_clusterwide')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            SECTION1_NAME: None
        })

        # set only section-2
        self.instance.set_variable('config', {
            SECTION2_NAME: SECTION2_BODY,
        })
        self.instance.clear_calls('config_patch_clusterwide')

        # delete section-1
        res = call_config_app(self.console_sock, {
            SECTION1_NAME: {
                'deleted': True,
            }
        })
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('config_patch_clusterwide')
        self.assertEqual(len(calls), 0)

        # set two sections
        self.instance.set_variable('config', {
            SECTION1_NAME: SECTION1_BODY,
            SECTION2_NAME: SECTION2_BODY,
        })
        self.instance.clear_calls('config_patch_clusterwide')

        # set deleted to False for section-1
        res = call_config_app(self.console_sock, {
            SECTION1_NAME: {
                'deleted': False,
                'body': SECTION1_BODY,
            }
        })
        self.assertTrue(res.success, msg=res.msg)
        self.assertFalse(res.changed)

        calls = self.instance.get_calls('config_patch_clusterwide')
        self.assertEqual(len(calls), 0)

    def test_changing_section(self):
        SECTION1_NAME = 'section-1'
        SECTION1_BODY = 'SECTION-1 BODY'
        SECTION2_NAME = 'section-2'
        SECTION2_BODY = 'SECTION-2 BODY'

        SECTION1_NEW_BODY = {'hi': 'I am section-1 new body'}

        # set two sections
        self.instance.set_variable('config', {
            SECTION1_NAME: SECTION1_BODY,
            SECTION2_NAME: SECTION2_BODY,
        })
        self.instance.clear_calls('config_patch_clusterwide')

        # change only section-1
        res = call_config_app(self.console_sock, {
            SECTION1_NAME: {
                'body': SECTION1_NEW_BODY,
            },
            SECTION2_NAME: {
                'body': SECTION2_BODY,
            }
        })
        self.assertTrue(res.success, msg=res.msg)
        self.assertTrue(res.changed)

        calls = self.instance.get_calls('config_patch_clusterwide')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {
            SECTION1_NAME: SECTION1_NEW_BODY
        })

    def test_patch_config_fails(self):
        SECTION_NAME = 'new-section'
        SECTION_BODY = 'SECTION BODY'
        SECTION_NEW_BODY = 'NEW SECTION BODY'

        self.instance.set_variable('config', {
            SECTION_NAME: SECTION_BODY
        })
        self.instance.clear_calls('config_patch_clusterwide')
        self.instance.set_fail_on('config_patch_clusterwide')

        # change section
        res = call_config_app(self.console_sock, {
            SECTION_NAME: {
                'body': SECTION_NEW_BODY,
            },
        })
        self.assertFalse(res.success)
        self.assertIn('Config patch failed', res.msg)
        self.assertIn('cartridge err', res.msg)

    def tearDown(self):
        self.instance.stop()
