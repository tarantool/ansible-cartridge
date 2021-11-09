import re
import sys

from testinfra.modules.file import File

import utils

testinfra_hosts = utils.get_testinfra_hosts()


def listdir(self):
    out = self.run_test("ls -1 -q -- %s", self.path)
    if out.rc != 0:
        raise RuntimeError("Unexpected output {}".format(out))
    return out.stdout.splitlines()


if sys.version_info[0] == 2:
    File.listdir = listdir


def test_dists_rotated(host):
    app_name = utils.get_app_name()
    app_install_dir = host.file('/usr/share/tarantool')

    dist_dir_rgx = r'^%s-\d+\.\d+\.\d+-\d+(-\S+)?$' % app_name

    dists = list(filter(
        lambda filename: re.match(dist_dir_rgx, filename) is not None,
        app_install_dir.listdir()
    ))

    assert dists == ['myapp-5.0.0-0-with-c-2.6.0']
