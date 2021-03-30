import os
import shutil
import sys
import tempfile
import time
import unittest

import module_utils.helpers as helpers

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_get_dist_dirs_to_remove import get_dist_dirs_to_remove


def call_get_dist_dirs_to_remove(app_name, app_install_dir, keep_num_latest_dists):
    return get_dist_dirs_to_remove({
        'app_name': app_name,
        'app_install_dir': app_install_dir,
        'keep_num_latest_dists': keep_num_latest_dists,
    })


APP_NAME = 'myapp'


def create_dir(path):
    os.makedirs(path)
    time.sleep(0.01)


def create_file(path):
    with open(path, 'w') as f:
        f.write("Hi")
    time.sleep(0.01)


class TestGetNeedsRestart(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

        self.app_install_dir = tempfile.mkdtemp()

        # create app dist dir
        create_dir(os.path.join(self.app_install_dir, '%s-0.0.1-0' % APP_NAME))

        # create stateboard dist dir - it shouldn't be removed
        create_dir(os.path.join(self.app_install_dir, helpers.get_instance_id(APP_NAME, stateboard=True)))

        # create instances dist dirs - it shouldn't be removed
        for instance_name in ['i-1', 'i-2', 'i-3']:
            create_dir(os.path.join(self.app_install_dir, helpers.get_instance_id(APP_NAME, instance_name)))

        # create file with <app-name>-<version> name
        create_file(os.path.join(self.app_install_dir, '%s-0.1.0-0' % APP_NAME))

        # create other app dist dirs
        other_app_versions = ['1.0.0-0', '2.0.0-0']
        for version in other_app_versions:
            create_dir(os.path.join(self.app_install_dir, '%s-%s' % ('XXXX', version)))

        # create app dist dirs
        versions = ['1.0.0-0', '2.0.0-0', '3.0.0-0-bbbbb', '3.0.0-0-aaa']
        for version in versions:
            create_dir(os.path.join(self.app_install_dir, '%s-%s' % (APP_NAME, version)))

        # create one more other app dist dirs
        other_app_versions = ['1.0.0-0', '2.0.0-0']
        for version in other_app_versions:
            create_dir(os.path.join(self.app_install_dir, '%s-%s' % ('YYY', version)))

        # create file with <app-name>-<version> name
        create_file(os.path.join(self.app_install_dir, '%s-6.0.0-0' % APP_NAME))

        # create one more app dist dir
        create_dir(os.path.join(self.app_install_dir, '%s-4.0.0-0' % APP_NAME))

    def test_get_dist_dirs_to_remove(self):
        res = call_get_dist_dirs_to_remove(APP_NAME, self.app_install_dir, 2)
        self.assertFalse(res.failed)
        self.assertEqual(
            set(res.fact),
            {
                os.path.join(self.app_install_dir, '%s-%s' % (APP_NAME, version))
                for version in ['3.0.0-0-bbbbb', '2.0.0-0', '1.0.0-0', '0.0.1-0']
            },
        )

    def test_retention_is_big(self):
        res = call_get_dist_dirs_to_remove(APP_NAME, self.app_install_dir, 20)
        self.assertFalse(res.failed)
        self.assertEqual(len(res.fact), 0)

    def test_negative_or_zero_retention(self):
        res = call_get_dist_dirs_to_remove(APP_NAME, self.app_install_dir, 0)
        self.assertTrue(res.failed)
        self.assertIn('"keep_num_latest_dists" should be > 0', res.msg)

        res = call_get_dist_dirs_to_remove(APP_NAME, self.app_install_dir, -3)
        self.assertTrue(res.failed)
        self.assertIn('"keep_num_latest_dists" should be > 0', res.msg)

    def tearDown(self):
        shutil.rmtree(self.app_install_dir)
