import unittest

import tempfile
import shutil
import os
import time

from library.cartridge_set_dist_dirs_to_remove import get_dist_dirs_to_remove


def call_get_dist_dirs_to_remove(app_name, app_install_dir, dists_retention_num):
    return get_dist_dirs_to_remove({
        'app_name': app_name,
        'app_install_dir': app_install_dir,
        'dists_retention_num': dists_retention_num,
    })


APP_NAME = 'myapp'


def create_dir(path):
    os.makedirs(path)
    time.sleep(0.01)


def create_file(path):
    with open(path, 'w') as f:
        f.write("Hi")
    time.sleep(0.01)


class TestSetNeedsRestart(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

        self.app_install_dir = tempfile.mkdtemp()

        # create app dist dir
        create_dir(os.path.join(self.app_install_dir, '%s-0.0.1-0' % APP_NAME))

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
            set(res.facts['dists_dirs_to_remove']),
            {
                os.path.join(self.app_install_dir, '%s-%s' % (APP_NAME, version))
                for version in ['3.0.0-0-bbbbb', '2.0.0-0', '1.0.0-0', '0.0.1-0']
            },
        )

    def test_retention_is_big(self):
        res = call_get_dist_dirs_to_remove(APP_NAME, self.app_install_dir, 20)
        self.assertFalse(res.failed)
        self.assertEqual(len(res.facts['dists_dirs_to_remove']), 0)

    def test_negative_or_zero_retention(self):
        res = call_get_dist_dirs_to_remove(APP_NAME, self.app_install_dir, 0)
        self.assertTrue(res.failed)
        self.assertIn('"dists_retention_num" should be > 0', res.msg)

        res = call_get_dist_dirs_to_remove(APP_NAME, self.app_install_dir, -3)
        self.assertTrue(res.failed)
        self.assertIn('"dists_retention_num" should be > 0', res.msg)

    def tearDown(self):
        shutil.rmtree(self.app_install_dir)
