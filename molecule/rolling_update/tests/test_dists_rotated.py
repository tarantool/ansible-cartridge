import os
import re

import testinfra.utils.ansible_runner


ansible_runner = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
)
testinfra_hosts = ansible_runner.get_hosts('all')

APP_NAME = 'myapp'


def test_dists_rotated(host):
    app_install_dir = host.file('/usr/share/tarantool')

    DIST_DIR_RGX = r'^%s-\d+\.\d+\.\d+-\d+(-\S+)?$' % APP_NAME

    dists = list(filter(
        lambda filename: re.match(DIST_DIR_RGX, filename) is not None,
        app_install_dir.listdir()
    ))

    assert dists == ['myapp-5.0.0-0-with-c-2.5.0']
