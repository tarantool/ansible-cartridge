#!/usr/bin/env python

import json
import os
import uuid
import zipfile

from ansible.module_utils.helpers import Helpers as helpers
from ansible.module_utils.urls import open_url, basic_auth_header

argument_spec = {
    'local_config_path': {'required': True, 'type': 'str'},
    'remote_dir': {'required': False, 'type': 'str', 'default': '/tmp/'},
    'upload_mode': {'required': False, 'type': 'str'},
    'console_sock': {'required': False, 'type': 'str'},
    'upload_url': {'required': False, 'type': 'str'},
    'cluster_cookie': {'required': False, 'type': 'str'},
    'tdg_token': {'required': False, 'type': 'str'},
}

LUA_MODE = 'lua'
HTTP_MODE = 'http'
TDG_MODE = 'tdg'

FILE_OUTPUT_FORMAT = 'file'
DIR_OUTPUT_FORMAT = 'dir'
ZIP_OUTPUT_FORMAT = 'zip'


####################
# Apply functions  #
####################


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


def send_on_http(upload_url, headers, config_path):
    headers.update({
        'Content-Length': os.stat(config_path).st_size
    })

    with open(config_path, 'rb') as data:
        try:
            resp = open_url(upload_url, method='PUT', headers=headers, data=data)
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


####################
# Prepare config   #
####################


def pack_zip(path):
    zip_config_path = os.path.abspath(os.path.join(path, os.pardir, 'config-%s.zip' % str(uuid.uuid4())))

    with zipfile.ZipFile(zip_config_path, 'w') as zf:
        for root, _, file_paths in os.walk(path):
            rel_dir_path = os.path.relpath(root, path)
            for file_path in file_paths:
                rel_file_path = os.path.join(rel_dir_path, file_path)
                zf.write(os.path.join(path, rel_file_path), rel_file_path)

    return zip_config_path


def unpack_zip(path):
    path_to_extract = os.path.abspath(os.path.join(path, os.pardir, 'config-%s' % str(uuid.uuid4())))

    with zipfile.ZipFile(path, 'r') as zip_ref:
        zip_ref.extractall(path_to_extract)

    return path_to_extract


def prepare_config(config_path, output_format, upload_mode):
    if output_format not in [FILE_OUTPUT_FORMAT, DIR_OUTPUT_FORMAT, ZIP_OUTPUT_FORMAT]:
        raise AssertionError("Unknown output format '%s'" % output_format)

    if os.path.isdir(config_path):
        if output_format == ZIP_OUTPUT_FORMAT:
            config_path = pack_zip(config_path)

        elif output_format != DIR_OUTPUT_FORMAT:
            raise AssertionError("Impossible to load directory by '%s' upload mode!" % upload_mode)

    else:
        if output_format == DIR_OUTPUT_FORMAT:
            file_ext = os.path.splitext(config_path)[1]
            if file_ext == '.zip':
                config_path = unpack_zip(config_path)
            else:
                raise AssertionError('Impossible to unpack config file!')

        elif output_format != FILE_OUTPUT_FORMAT:
            raise AssertionError("Impossible to load file by '%s' upload mode!" % upload_mode)

    return config_path


####################
# TDG helpers      #
####################


def get_tdg_upload_mode(console_sock):
    if console_sock is None:
        return 'http'

    control_console = helpers.get_control_console(console_sock)
    return control_console.eval_res_err('''
        if rawget(_G, 'admin') ~= nil and rawget(_G.admin, 'upload_config_api') ~= nil then
            return 'lua'
        end
        return 'http'
    ''')[0]


def get_tdg_http_headers(console_sock, tdg_token):
    if tdg_token is None:
        return {}

    assert console_sock is not None, "Console socket is required for TDG mode"
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


####################
# Mode selectors   #
####################


def prepare_upload_mode(upload_mode, remote_config_path):
    if upload_mode is not None:
        upload_mode = upload_mode.lower()

    if not os.path.isdir(remote_config_path):
        if os.path.splitext(remote_config_path)[1] in ['.yml', '.yaml']:
            upload_mode = upload_mode or LUA_MODE
        else:
            upload_mode = upload_mode or HTTP_MODE
    else:
        upload_mode = upload_mode or HTTP_MODE

    return upload_mode


def get_output_format_and_apply_config_func_for_lua(console_sock):
    assert console_sock is not None, "Console socket is required for Lua mode"

    control_console = helpers.get_control_console(console_sock)

    return FILE_OUTPUT_FORMAT, lambda path: patch_file_clusterwide(control_console, path)


def get_output_format_and_apply_config_func_for_http(upload_url, cluster_cookie):
    assert cluster_cookie is not None, 'Cluster cookie is required for HTTP mode'
    assert upload_url is not None, 'Upload URL is required for HTTP mode'

    headers = {'Authorization': basic_auth_header('admin', cluster_cookie)}

    return FILE_OUTPUT_FORMAT, lambda path: send_on_http(upload_url, headers, path)


def get_output_format_and_apply_config_func_for_tdg(console_sock, upload_url, tdg_token):
    tdg_upload_mode = get_tdg_upload_mode(console_sock)

    if tdg_upload_mode == 'http':
        assert upload_url is not None, 'Upload URL is required for TDG mode'

        headers = get_tdg_http_headers(console_sock, tdg_token)

        return ZIP_OUTPUT_FORMAT, lambda path: send_on_http(upload_url, headers, path)

    elif tdg_upload_mode == 'lua':
        return DIR_OUTPUT_FORMAT, lambda path: apply_tdg_config(console_sock, path)

    raise AssertionError("Unknown TDG upload mode '%s'" % tdg_upload_mode)


def get_output_format_and_apply_config_func(
    upload_mode,
    console_sock=None,
    upload_url=None,
    cluster_cookie=None,
    tdg_token=None,
):
    if upload_mode == LUA_MODE:
        return get_output_format_and_apply_config_func_for_lua(console_sock)

    elif upload_mode == HTTP_MODE:
        return get_output_format_and_apply_config_func_for_http(upload_url, cluster_cookie)

    elif upload_mode == TDG_MODE:
        return get_output_format_and_apply_config_func_for_tdg(console_sock, upload_url, tdg_token)

    raise AssertionError("Unknown upload mode '%s'" % upload_mode)


####################
# Main function    #
####################


def apply_app_config(params):
    # We cannot use the fact 'dest' from the copy task,
    # because in the case of transferring a folder with one file,
    # 'dest' will contain the path to the file, not the path to the folder.
    # Therefore, we consider the path ourselves.
    remote_config_path = os.path.join(params['remote_dir'], os.path.basename(params['local_config_path']))

    upload_mode = prepare_upload_mode(
        upload_mode=params['upload_mode'],
        remote_config_path=remote_config_path,
    )

    output_format, apply_config_func = get_output_format_and_apply_config_func(
        upload_mode,
        console_sock=params['console_sock'],
        upload_url=params['upload_url'],
        cluster_cookie=params['cluster_cookie'],
        tdg_token=params['tdg_token'],
    )

    temp_paths = [remote_config_path]
    new_config_path = prepare_config(remote_config_path, output_format, upload_mode)
    if new_config_path != remote_config_path:
        temp_paths.append(new_config_path)

    changed = apply_config_func(new_config_path)

    return helpers.ModuleRes(changed=changed, fact={
        'temp_paths': temp_paths,
        'upload_url': params['upload_url'],
        'upload_mode': params['upload_mode'],
    })


if __name__ == '__main__':
    helpers.execute_module(argument_spec, apply_app_config)
