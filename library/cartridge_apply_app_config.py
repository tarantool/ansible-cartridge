#!/usr/bin/env python

import json
import os
import zipfile

from ansible.module_utils.helpers import Helpers as helpers
from ansible.module_utils.urls import open_url, basic_auth_header

argument_spec = {
    'local_config_path': {'required': True, 'type': 'str'},
    'remote_dir': {'required': False, 'type': 'str', 'default': '/tmp/'},
    'upload_mode': {'required': False, 'type': 'str'},
    'console_sock': {'required': False, 'type': 'str'},
    'http_port': {'required': False, 'type': 'int'},
    'cluster_cookie': {'required': False, 'type': 'str'},
    'tdg_token': {'required': False, 'type': 'str'},
}

LUA_MODE = 'lua'
HTTP_MODE = 'http'
TDG_MODE = 'tdg'

PURE_DIR_MODE = 'pure'
ZIP_DIR_MODE = 'zip'


def patch_file_clusterwide(control_console, file_path):
    file_ext = os.path.splitext(file_path)[1]
    assert file_ext in ['.yml', '.yaml'], "Impossible to use '%s' file in patch clusterwide function" % file_ext

    new_sections, err = helpers.read_yaml_file(control_console, file_path)
    assert err is None, err

    old_sections, err = helpers.get_clusterwide_config(control_console)
    assert err is None, err

    for section, value in old_sections.items():
        new_sections[section] = new_sections.get(section)

    changed, err = helpers.patch_clusterwide_config(control_console, new_sections)
    assert err is None, err
    return changed


def send_on_http(http_port, headers, config_path):
    url = 'http://127.0.0.1:{port}/admin/config'.format(port=http_port)
    headers.update({
        'Content-Length': os.stat(config_path).st_size
    })

    with open(config_path, 'rb') as data:
        try:
            resp = open_url(url, method='PUT', headers=headers, data=data)
        except Exception as e:
            assert hasattr(e, 'code'), str(e)
            resp = e

    if not 200 <= resp.code <= 299:
        error = ''
        try:
            error = resp.read()
            error = json.loads(error)
            if "str" in error:
                error = error["str"]
        except Exception:
            pass

        raise AssertionError("Status: {}. Body: '{}'".format(resp.code, error))

    return True


def apply_tdg_config(console_sock, path):
    control_console = helpers.get_control_console(console_sock)
    _, err = control_console.eval_res_err('''
        return admin.upload_config_api(...)
    ''', path)
    assert err is None, err
    return True


def apply_dir_config(dir_mode, apply_func, config_path):
    if dir_mode == ZIP_DIR_MODE:
        zip_config_path = os.path.join(config_path, os.pardir, 'config.zip')

        with zipfile.ZipFile(zip_config_path, 'w') as zf:
            for root, _, file_paths in os.walk(config_path):
                rel_dir_path = os.path.relpath(root, config_path)
                for file_path in file_paths:
                    rel_file_path = os.path.join(rel_dir_path, file_path)
                    zf.write(os.path.join(config_path, rel_file_path), rel_file_path)

        config_path = zip_config_path

    elif dir_mode != PURE_DIR_MODE:
        raise AssertionError("Unknown upload directory mode '%s'" % dir_mode)

    return apply_func(config_path)


def get_tdg_upload_mode(console_sock):
    if console_sock is None:
        return 'http'

    control_console = helpers.get_control_console(console_sock)
    return control_console.eval_res_err('''
        if admin ~= nil and admin.upload_config_api ~= nil then
            return 'lua'
        end
        return 'http'
    ''')[0]


def get_tdg_auth_headers(console_sock, tdg_token):
    if tdg_token is None:
        return {}

    assert console_sock is not None, "Console socket is required for TDG endpoint"
    control_console = helpers.get_control_console(console_sock)

    tdg_version = control_console.eval_res_err('''
        local ok, app_version = pcall(require, 'common.app_version')
        if not ok then
            return '1.6.0-0-0'
        end
        return app_version.get()
    ''')[0].split('.')

    if tdg_version[0] == 'scm-1':
        return {
            'auth-token': tdg_token,  # TDG <= 1.6
            'Authorization': 'Bearer ' + tdg_token,  # TDG >= 1.7
        }

    major = int(tdg_version[0])
    minor = int(tdg_version[1])
    if major < 1 or major == 1 and minor <= 6:
        return {'auth-token': tdg_token}
    return {'Authorization': 'Bearer ' + tdg_token}


def get_upload_mode(upload_mode, remote_config_path):
    if upload_mode is not None:
        upload_mode = upload_mode.lower()

    if not os.path.isdir(remote_config_path):
        if os.path.splitext(remote_config_path)[1] in ['.yml', '.yaml']:
            upload_mode = upload_mode or LUA_MODE
        else:
            upload_mode = upload_mode or HTTP_MODE

        assert upload_mode in [LUA_MODE, HTTP_MODE], \
            'File config available only for Lua or HTTP endpoints'
    else:
        upload_mode = upload_mode or HTTP_MODE

        assert upload_mode in [HTTP_MODE, TDG_MODE], \
            'Directory config available only for HTTP or TDG endpoints'

    return upload_mode


def get_apply_config_func_for_lua(console_sock):
    assert console_sock is not None, "Console socket is required for Cartridge endpoint"

    control_console = helpers.get_control_console(console_sock)

    return lambda path: patch_file_clusterwide(control_console, path)


def get_apply_config_func_for_http(http_port, cluster_cookie):
    assert cluster_cookie is not None, 'Cluster cookie is required for HTTP endpoint'
    assert http_port is not None, 'HTTP port is required for HTTP endpoint'

    headers = {'Authorization': basic_auth_header('admin', cluster_cookie)}

    return lambda path: send_on_http(http_port, headers, path)


def get_apply_config_func_for_tdg(console_sock, http_port, tdg_token):
    tdg_upload_mode = get_tdg_upload_mode(console_sock)

    if tdg_upload_mode == 'http':
        assert http_port is not None, 'HTTP port is required for TDG endpoint'

        headers = get_tdg_auth_headers(console_sock, tdg_token)

        return lambda path: send_on_http(http_port, headers, path), ZIP_DIR_MODE

    elif tdg_upload_mode == 'lua':
        return lambda path: apply_tdg_config(console_sock, path), PURE_DIR_MODE

    raise AssertionError("Unknown TDG upload mode '%s'" % tdg_upload_mode)


def get_apply_config_func(upload_mode, console_sock=None, http_port=None, cluster_cookie=None, tdg_token=None):
    dir_mode = ZIP_DIR_MODE

    if upload_mode == LUA_MODE:
        apply_func = get_apply_config_func_for_lua(console_sock)

    elif upload_mode == HTTP_MODE:
        apply_func = get_apply_config_func_for_http(http_port, cluster_cookie)

    elif upload_mode == TDG_MODE:
        apply_func, dir_mode = get_apply_config_func_for_tdg(console_sock, http_port, tdg_token)

    else:
        raise AssertionError("Unknown upload mode '%s'" % upload_mode)

    return apply_func, dir_mode


def apply_app_config(params):
    # We cannot use the fact 'dest' from the copy task,
    # because in the case of transferring a folder with one file,
    # 'dest' will contain the path to the file, not the path to the folder.
    # Therefore, we consider the path ourselves.
    remote_config_path = os.path.join(params['remote_dir'], os.path.basename(params['local_config_path']))

    upload_mode = get_upload_mode(
        upload_mode=params['upload_mode'],
        remote_config_path=remote_config_path,
    )

    apply_config, dir_mode = get_apply_config_func(
        upload_mode,
        console_sock=params['console_sock'],
        http_port=params['http_port'],
        cluster_cookie=params['cluster_cookie'],
        tdg_token=params['tdg_token'],
    )

    if os.path.isdir(remote_config_path):
        changed = apply_dir_config(dir_mode, apply_config, remote_config_path)
    else:
        changed = apply_config(remote_config_path)

    return helpers.ModuleRes(changed=changed, fact={'dest_path': remote_config_path})


if __name__ == '__main__':
    helpers.execute_module(argument_spec, apply_app_config)
