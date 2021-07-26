import re

import utils

testinfra_hosts = utils.get_testinfra_hosts()


def test_dists_rotated(host):
    app_name = utils.get_app_name()
    app_install_dir = host.file('/usr/share/tarantool')

    dist_dir_rgx = r'^%s-\d+\.\d+\.\d+-\d+(-\S+)?$' % app_name

    dists = list(filter(
        lambda filename: re.match(dist_dir_rgx, filename) is not None,
        app_install_dir.listdir()
    ))

    assert dists == ['myapp-5.0.0-0-with-c-2.5.0']
