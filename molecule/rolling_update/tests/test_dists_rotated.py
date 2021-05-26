import re

from importlib.machinery import SourceFileLoader
utils = SourceFileLoader("utils", "./molecule/common/tests/utils.py").load_module()


testinfra_hosts = utils.get_testinfra_hosts()


def test_dists_rotated(host):
    app_name = utils.get_app_name()
    app_install_dir = host.file('/usr/share/tarantool')

    DIST_DIR_RGX = r'^%s-\d+\.\d+\.\d+-\d+(-\S+)?$' % app_name

    dists = list(filter(
        lambda filename: re.match(DIST_DIR_RGX, filename) is not None,
        app_install_dir.listdir()
    ))

    assert dists == ['myapp-5.0.0-0-with-c-2.5.0']
