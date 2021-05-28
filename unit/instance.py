import json
import os
import re
import socket
import textwrap
import sys
from subprocess import Popen

import tenacity

from unit.os_mock import OsPathExistsMock, OsPathGetMTimeMock

instance_app_dir = os.path.realpath(
    os.path.join(
        os.path.dirname(__file__), 'mock'
    )
)


class Instance:
    APP_NAME = 'myapp'
    INSTANCE_NAME = 'instance-1'
    COOKIE = 'cookie'

    INSTANCE_CONF_PATH = '/etc/tarantool/conf.d/{}.{}.yml'.format(APP_NAME, INSTANCE_NAME)
    instance_id = '{}.{}'.format(APP_NAME, INSTANCE_NAME)
    APP_CONF_PATH = '/etc/tarantool/conf.d/{}.yml'.format(APP_NAME)
    APP_CODE_PATH = '/usr/share/tarantool/{}'.format(APP_NAME)

    DATE_YESTERDAY = -1
    DATE_TODAY = 0
    DATE_TOMORROW = 1

    def __init__(self):
        self.console_sock = os.path.join(os.getcwd(), 'instance.sock')
        self.cluster_cookie = 'secret'

        self.script = "init.lua"

        self.process = None
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        self.__original_exists = os.path.exists
        self.__original_getmtime = os.path.getmtime

        os.path.exists = OsPathExistsMock()
        os.path.getmtime = OsPathGetMTimeMock()

    def __del__(self):
        self.stop()

        os.path.exists = self.__original_exists
        os.path.getmtime = self.__original_getmtime

        if os.path.exists(self.console_sock):
            os.remove(self.console_sock)

    @tenacity.retry(wait=tenacity.wait_fixed(0.1),
                    stop=tenacity.stop_after_delay(5))
    def _connect(self):
        self.sock.connect(self.console_sock)
        self.sock.recv(1024)

    def start(self, debug=False):
        command = ["./%s" % self.script]
        cwd = instance_app_dir

        env = os.environ.copy()
        env['TARANTOOL_CONSOLE_SOCK'] = self.console_sock

        with open(os.devnull, 'w') as FNULL:
            stdout = FNULL
            stderr = FNULL
            if debug:
                stdout = sys.stdout
                stderr = sys.stderr

            self.process = Popen(command, env=env, cwd=cwd, stdout=stdout, stderr=stderr)

        self._connect()

        files = {
            self.console_sock: '',
            self.APP_CODE_PATH: '',
        }
        for path, content in files.items():
            self.write_file(path, content)
            self.set_path_m_time(path, self.DATE_TODAY)

        self.set_default_instance_config()
        self.set_default_app_config()

    def eval(self, func_body, *args):
        def sendall(msg):
            return self.sock.sendall(msg.encode())

        def recvall():
            data = ''
            while True:
                chunk = self.sock.recv(1024).decode()
                # It is correct because of cmd structure: it always returns a value
                if chunk == '':
                    raise Exception(
                        'Error: broken pipe. '
                        'Probably, the instance was not bootstrapped yet to perform this operation'
                    )
                data = data + chunk
                if data.endswith('\n...\n'):
                    break
            return data

        if not args:
            args = []
        args_encoded = json.dumps(args)

        cmd_fmt = textwrap.dedent('''
            local function func(...)
                {func_body}
            end
            local args = require('json').decode('{args_encoded}')
            local ret = {{
                load(
                    'local func, args = ... return func(unpack(args))',
                    '@eval'
                )(func, args)
            }}
            return string.hex(require('json').encode(ret))
        ''')

        cmd = cmd_fmt.format(func_body=func_body, args_encoded=args_encoded)

        lines = [line.strip() for line in cmd.split('\n') if line.strip()]
        cmd = ' '.join(lines) + '\n'

        sendall(cmd)

        raw_output = recvall()

        hex_output = re.sub(r"^---\n-\s+?", '', raw_output)
        hex_output = re.sub(r"'?\n...\n$", '', hex_output)
        hex_output = re.sub(r"\n\s*", '', hex_output)

        if hex_output.startswith("error:"):
            err = re.sub(r"error:\s+", '', hex_output)
            raise Exception(err)

        output = bytearray.fromhex(hex_output).decode('utf-8')

        return json.loads(output)

    def eval_res_err(self, func_body, *args):
        data = self.eval(func_body, *args)

        assert len(data) <= 2

        if len(data) == 0:
            # return nil
            data.append(None)

        if len(data) == 1:
            # return res
            data.append(None)

        # err can be tarantool/errors instance
        if isinstance(data[1], dict) and data[1].get('err') is not None:
            data[1] = data[1].get('err')

        return data

    def stop(self):
        self.sock.close()
        if self.process is not None:
            self.process.kill()
            self.process.communicate()

    def write_file(self, path, content=''):
        os.path.exists.set_exists(path)
        self.eval_res_err('''
            local path, content = ...
            require('fio').path.write_file({
                path = path,
                content = content,
            })
        ''', path, content)

    def remove_file(self, path):
        os.path.exists.set_not_exists(path)
        self.eval_res_err('''
            require('fio').path.remove_file(...)
        ''', path)

    def set_instance_config(self, config,
                            instance_conf_file=None,
                            conf_section_name=None):
        if instance_conf_file is None:
            instance_conf_file = Instance.INSTANCE_CONF_PATH

        if conf_section_name is None:
            conf_section_name = Instance.instance_id

        params = ', '.join([
            '{}: {}'.format(k, v)
            for k, v in config.items()
        ])
        conf = '{conf_section_name}: {{ {params} }}'.format(
            conf_section_name=conf_section_name,
            params=params
        )
        self.write_file(instance_conf_file, conf)

    def set_app_config(self, config, set_cookie=True):
        config = config.copy()
        if set_cookie:
            config.update({'cluster_cookie': self.COOKIE})

        params = ', '.join([
            '{}: {}'.format(k, v)
            for k, v in config.items()
        ])
        conf = '{app_name}: {{ {params} }}'.format(
            app_name=self.APP_NAME,
            params=params
        )
        self.write_file(self.APP_CONF_PATH, conf)

    def set_default_instance_config(self):
        self.set_instance_config({})

    def set_default_app_config(self):
        self.set_app_config({
            'cluster_cookie': self.COOKIE
        })

    @staticmethod
    def set_path_m_time(path, m_time):
        os.path.getmtime.set_m_time(path, m_time)

    def set_box_cfg_function(self, value=True):
        self.eval_res_err('''
            require('cartridge').internal.set_box_cfg_function(...)
        ''', value)

    def set_cartridge_version(self, version):
        self.eval_res_err('''
            require('cartridge').VERSION = ...
        ''', version)

    def set_fail_on(self, func_name, value=True):
        self.eval_res_err('''
            local func_name, value = ...
            require('cartridge').internal.set_fail(func_name, value)
        ''', func_name, value)

    def clear_calls(self, func_name):
        self.eval_res_err('''
            require('cartridge').internal.clear_calls(...)
        ''', func_name)

    def get_calls(self, func_name):
        calls, _ = self.eval_res_err('''
            return require('cartridge').internal.get_calls(...)
        ''', func_name)
        return calls

    def set_variable(self, name, value):
        self.eval_res_err('''
            local name, value = ...
            require('cartridge').internal.set_variable(name, value)
        ''', name, value)

    def set_box_cfg(self, **new_box_cfg):
        self.eval_res_err('''
            require('cartridge').internal.set_box_cfg(...)
        ''', new_box_cfg)

    def set_membership_members(self, specified_members, with_payload=True):
        members = {}

        for m in specified_members:
            uri = m['uri']
            member = {
                'uri': uri,
                'status': m.get('status', 'alive'),
                'incarnation': 1,
            }

            if with_payload:
                member.update({
                    'payload': {
                        'uuid': m.get('uuid'),
                        'alias': m.get('alias'),
                        'state': m.get('state'),
                    }
                })

            members[uri] = member

        self.set_variable('membership_members', members)

    def add_membership_members(self, members):
        self.eval_res_err('''
            require('cartridge').internal.add_membership_members(...)
        ''', members)

    def set_member_status(self, uri, status):
        self.eval_res_err('''
            require('cartridge').internal.set_member_status(...)
        ''', uri, status)

    def add_replicaset(self, **kwargs):
        self.eval_res_err('''
            require('cartridge').internal.add_replicaset(...)
        ''', kwargs)

    def cfg_roles(self, *roles):
        self.eval_res_err('''
            require('cartridge').internal.cfg_roles(...)
        ''', roles)

    def bootstrap_cluster(self):
        self.eval_res_err('''
            require('cartridge').internal.bootstrap_cluster()
        ''')

    def set_auth(self, auth_cfg):
        self.eval_res_err('''
            require('cartridge').internal.set_auth(...)
        ''', auth_cfg)

    def set_users(self, users):
        self.eval_res_err('''
            require('cartridge').internal.set_users(...)
        ''', users)

    def set_failover_params(self, **kwargs):
        self.eval_res_err('''
            require('cartridge').internal.set_failover_params(...)
        ''', kwargs)

    def set_config(self, config):
        self.eval_res_err('''
            require('cartridge').internal.set_config(...)
        ''', config)
