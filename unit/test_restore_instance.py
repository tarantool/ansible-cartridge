import sys
import unittest

import module_utils.helpers as helpers

sys.modules['ansible.module_utils.helpers'] = helpers
from library.cartridge_restore_instance import is_path_of_instance


class TestRestoreInstance(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_is_path_of_instance(self):
        self.assertTrue(is_path_of_instance('/backups/myapp.i-1.tar.gz', 'myapp.i-1'))
        self.assertTrue(is_path_of_instance('/backups/myapp.i-1.2020-01-01.tar.gz', 'myapp.i-1'))
        self.assertTrue(is_path_of_instance('/backups/myapp.i-1.2020-01-01-010101.tar.gz', 'myapp.i-1'))
        self.assertTrue(is_path_of_instance('/backups/myapp.i-1.1627650508.tar.gz', 'myapp.i-1'))
        self.assertTrue(is_path_of_instance('/backups/backup.myapp.i-1.tar.gz', 'myapp.i-1'))
        self.assertTrue(is_path_of_instance('/backups/myapp.i-1/', 'myapp.i-1'))

        self.assertFalse(is_path_of_instance('/backups/myapp.i-11.tar.gz', 'myapp.i-1'))
        self.assertFalse(is_path_of_instance('/backups/myapp.i-1.1.tar.gz', 'myapp.i-1'))
        self.assertFalse(is_path_of_instance('/backups/myapp.i-1-1.tar.gz', 'myapp.i-1'))
        self.assertFalse(is_path_of_instance('/backups/myapp.i-1-replica.tar.gz', 'myapp.i-1'))
