#!/usr/bin/env python

import json
import os
import zipfile

from ansible.module_utils.helpers import Helpers as helpers
from ansible.module_utils.urls import open_url, basic_auth_header

argument_spec = {
    'config_path': {'required': True, 'type': 'str'},
    'upload_endpoint': {'required': True, 'type': 'str'},
    'dir_upload_mode': {'required': False, 'type': 'str'},
    'console_sock': {'required': False, 'type': 'str'},
    'http_port': {'required': False, 'type': 'int'},
    'cluster_cookie': {'required': False, 'type': 'str'},
    'tdg_token': {'required': False, 'type': 'str'},
}

YML_DIR_UPLOAD_MODE = 'yml'
ZIP_DIR_UPLOAD_MODE = 'zip'


def patch_file_clusterwide(control_console, file_path):
    file_ext = os.path.splitext(file_path)[1]
    if file_ext not in ['.yml', '.yaml']:
        return None, "Impossible to use '%s' file in patch clusterwide function!" % file_ext

    new_sections, err = helpers.read_yaml_file(control_console, file_path)
    if err is not None:
        return None, err

    section_name = os.path.splitext(os.path.basename(file_path))[0]
    if section_name != 'config':
        new_sections = {section_name: new_sections}
    else:
        old_sections, err = helpers.get_clusterwide_config(control_console)
        if err is not None:
            return None, err

        for section, value in old_sections.items():
            new_sections[section] = new_sections.get(section)

    return helpers.patch_clusterwide_config(control_console, new_sections)


def send_on_http(http_port, headers, config_path):
    url = 'http://127.0.0.1:{port}/admin/config'.format(port=http_port)
    headers.update({
        'Content-Length': os.stat(config_path).st_size
    })

    with open(config_path, 'rb') as data:
        try:
            resp = open_url(url, method='PUT', headers=headers, data=data)
        except Exception as e:
            if not hasattr(e, 'code'):
                return None, str(e)
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

        return None, "Status: {}. Body: '{}'".format(resp.code, error)

    return True, None


def apply_yml_dir_config(apply_func, config_path):
    dir_changed = False
    for file in os.listdir(config_path):
        if os.path.splitext(file)[1] not in ['.yml', '.yaml']:
            continue

        changed, err = apply_func(os.path.join(config_path, file))
        if err is not None:
            return None, err
        if changed:
            dir_changed = True

    return dir_changed, None


def apply_zip_dir_config(apply_func, config_path):
    zip_config_path = os.path.join(config_path, os.pardir, 'config.zip')

    with zipfile.ZipFile(zip_config_path, 'w') as zf:
        for root, _, file_paths in os.walk(config_path):
            rel_dir_path = os.path.relpath(root, config_path)
            for file_path in file_paths:
                rel_file_path = os.path.join(rel_dir_path, file_path)
                zf.write(os.path.join(config_path, rel_file_path), rel_file_path)

    return apply_func(zip_config_path)


def apply_dir_config(dir_upload_mode, apply_func, config_path):
    if not dir_upload_mode:
        return None, "Parameter 'dir_upload_mode' is required for dir config"

    if dir_upload_mode == YML_DIR_UPLOAD_MODE:
        return apply_yml_dir_config(apply_func, config_path)

    if dir_upload_mode == ZIP_DIR_UPLOAD_MODE:
        return apply_zip_dir_config(apply_func, config_path)

    return None, "Unknown dir upload mode: '%s'" % dir_upload_mode


def get_tdg_auth_headers(console_sock, tdg_token):
    control_console = helpers.get_control_console(console_sock)
    tdg_version, _ = control_console.eval_res_err('''
        ok, app_version = pcall(require, 'common.app_version')
        if not ok:
            return '1.6.0-0-0'
        return app_version.get()
    ''').split('.')

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


def apply_app_config(params):
    config_path = params['config_path']
    upload_endpoint = params['upload_endpoint']
    dir_upload_mode = params['dir_upload_mode']
    console_sock = params['console_sock']
    http_port = params['http_port']
    cluster_cookie = params['cluster_cookie']
    tdg_token = params['tdg_token']

    if upload_endpoint == 'cartridge':
        dir_upload_mode = dir_upload_mode or YML_DIR_UPLOAD_MODE
        control_console = helpers.get_control_console(console_sock)

        def apply_config(path):
            return patch_file_clusterwide(control_console, path)

    elif upload_endpoint == 'http':
        dir_upload_mode = dir_upload_mode or YML_DIR_UPLOAD_MODE
        headers = {'Authorization': basic_auth_header('admin', cluster_cookie)}

        def apply_config(path):
            return send_on_http(http_port, headers, path)

    elif upload_endpoint == 'tdg':
        dir_upload_mode = dir_upload_mode or ZIP_DIR_UPLOAD_MODE
        headers = get_tdg_auth_headers(console_sock, tdg_token)

        def apply_config(path):
            return send_on_http(http_port, headers, path)

    else:
        return helpers.ModuleRes(failed=True, msg="Unknown upload endpoint '%s'" % upload_endpoint)

    if os.path.isdir(config_path):
        changed, err = apply_dir_config(dir_upload_mode, apply_config, config_path)
    else:
        changed, err = apply_config(config_path)

    if err:
        return helpers.ModuleRes(failed=True, msg=err)
    return helpers.ModuleRes(changed=changed)


if __name__ == '__main__':
    helpers.execute_module(argument_spec, apply_app_config)
