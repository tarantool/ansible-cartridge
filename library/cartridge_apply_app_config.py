#!/usr/bin/env python

import json
import os
import zipfile

from ansible.module_utils.helpers import Helpers as helpers
from ansible.module_utils.urls import open_url, basic_auth_header

argument_spec = {
    'local_config_path': {'required': True, 'type': 'str'},
    'remote_dir': {'required': False, 'type': 'str', 'default': '/tmp/'},
    'upload_endpoint': {'required': False, 'type': 'str'},
    'console_sock': {'required': False, 'type': 'str'},
    'http_port': {'required': False, 'type': 'int'},
    'cluster_cookie': {'required': False, 'type': 'str'},
    'tdg_token': {'required': False, 'type': 'str'},
}

LUA_ENDPOINT = 'lua'
HTTP_ENDPOINT = 'http'
TDG_ENDPOINT = 'tdg'

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


def get_upload_endpoint(upload_endpoint, remote_config_path):
    if upload_endpoint is not None:
        upload_endpoint = upload_endpoint.lower()

    if not os.path.isdir(remote_config_path):
        if os.path.splitext(remote_config_path)[1] in ['.yml', '.yaml']:
            upload_endpoint = upload_endpoint or LUA_ENDPOINT
        else:
            upload_endpoint = upload_endpoint or HTTP_ENDPOINT

        assert upload_endpoint in [LUA_ENDPOINT, HTTP_ENDPOINT], \
            'File config available only for Lua or HTTP endpoints'
    else:
        upload_endpoint = upload_endpoint or HTTP_ENDPOINT

        assert upload_endpoint in [HTTP_ENDPOINT, TDG_ENDPOINT], \
            'Directory config available only for HTTP or TDG endpoints'

    return upload_endpoint


def get_apply_config_func(upload_endpoint, console_sock=None, http_port=None, cluster_cookie=None, tdg_token=None):
    dir_mode = ZIP_DIR_MODE

    if upload_endpoint == LUA_ENDPOINT:
        assert console_sock is not None, "Console socket is required for Cartridge endpoint"
        control_console = helpers.get_control_console(console_sock)

        def apply_config(path):
            return patch_file_clusterwide(control_console, path)

    elif upload_endpoint == HTTP_ENDPOINT:
        assert cluster_cookie is not None, 'Cluster cookie is required for HTTP endpoint'
        assert http_port is not None, 'HTTP port is required for HTTP endpoint'
        headers = {'Authorization': basic_auth_header('admin', cluster_cookie)}

        def apply_config(path):
            return send_on_http(http_port, headers, path)

    elif upload_endpoint == TDG_ENDPOINT:
        tdg_upload_mode = get_tdg_upload_mode(console_sock)
        if tdg_upload_mode == 'http':
            assert http_port is not None, 'HTTP port is required for TDG endpoint'
            headers = get_tdg_auth_headers(console_sock, tdg_token)

            def apply_config(path):
                return send_on_http(http_port, headers, path)

        elif tdg_upload_mode == 'lua':
            dir_mode = PURE_DIR_MODE

            def apply_config(path):
                return apply_tdg_config(console_sock, path)

        else:
            raise AssertionError("Unknown TDG upload mode '%s'" % tdg_upload_mode)

    else:
        raise AssertionError("Unknown upload endpoint '%s'" % upload_endpoint)

    return apply_config, dir_mode


def apply_app_config(params):
    remote_config_path = os.path.join(params['remote_dir'], os.path.basename(params['local_config_path']))

    upload_endpoint = get_upload_endpoint(
        upload_endpoint=params['upload_endpoint'],
        remote_config_path=remote_config_path,
    )

    apply_config, dir_mode = get_apply_config_func(
        upload_endpoint,
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
