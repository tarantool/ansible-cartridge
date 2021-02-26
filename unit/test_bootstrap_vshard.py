import unittest

from unit.instance import Instance
from library.cartridge_bootstrap_vshard import bootstrap_vshard


def call_bootstrap_vshard(console_sock):
    return bootstrap_vshard({
        'console_sock': console_sock,
    })


class TestBootstrapVshard(unittest.TestCase):
    def setUp(self):
        self.cookie = 'secret'
        self.console_sock = './tmp/x.sock'

        self.instance = Instance(self.console_sock, self.cookie)
        self.instance.start()

    def test_can_not_bootstrap_vshard(self):
        self.instance.set_variable('can_bootstrap_vshard', False)

        res = call_bootstrap_vshard(self.console_sock)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertFalse(res.changed)

        self.assertEqual(len(self.instance.get_calls('bootstrap_vshard')), 0)

    def test_bootstrap_successfully(self):
        self.instance.set_variable('can_bootstrap_vshard', True)

        res = call_bootstrap_vshard(self.console_sock)
        self.assertFalse(res.failed, msg=res.msg)
        self.assertTrue(res.changed)

        self.assertEqual(len(self.instance.get_calls('bootstrap_vshard')), 1)

    def test_bootstrap_fails(self):
        self.instance.set_variable('can_bootstrap_vshard', True)
        self.instance.set_fail_on('bootstrap_vshard')

        res = call_bootstrap_vshard(self.console_sock)
        self.assertTrue(res.failed)
        self.assertIn('Vshard bootstrap failed', res.msg)
        self.assertIn('cartridge err', res.msg)

        self.assertEqual(len(self.instance.get_calls('bootstrap_vshard')), 1)

    def tearDown(self):
        self.instance.stop()
        del self.instance
