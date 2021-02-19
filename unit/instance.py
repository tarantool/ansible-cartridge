import json
import os
import re
import socket
from subprocess import Popen

import tenacity

from os_mock import OsPathExistsMock, OsPathGetMTimeMock

script_abspath = os.path.realpath(
    os.path.join(
        os.path.dirname(__file__), 'mock'
    )
)


class Instance:
    APP_NAME = 'myapp'
    INSTANCE_NAME = 'instance-1'
    COOKIE = 'cookie'

    INSTANCE_CONF_PATH = '/etc/tarantool/conf.d/{}.{}.yml'.format(APP_NAME, INSTANCE_NAME)
    CONF_SECTION = '{}.{}'.format(APP_NAME, INSTANCE_NAME)
    APP_CONF_PATH = '/etc/tarantool/conf.d/{}.yml'.format(APP_NAME)
    APP_CODE_PATH = '/usr/share/tarantool/{}'.format(APP_NAME)

    DATE_YESTERDAY = -1
    DATE_TODAY = 0
    DATE_TOMORROW = 1

    def __init__(self, console_sock, cluster_cookie):
        self.script = "init.lua"
        self.console_sock = console_sock
        self.cluster_cookie = cluster_cookie

        self.process = None
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        self.__original_exists = os.path.exists
        self.__original_getmtime = os.path.getmtime

        os.path.exists = OsPathExistsMock()
        os.path.getmtime = OsPathGetMTimeMock()

    def __del__(self):
        os.path.exists = self.__original_exists
        os.path.getmtime = self.__original_getmtime

        if os.path.exists(self.console_sock):
            os.remove(self.console_sock)

    @tenacity.retry(wait=tenacity.wait_fixed(0.1),
                    stop=tenacity.stop_after_delay(5))
    def _connect(self):
        self.sock.connect(self.console_sock)
        self.sock.recv(1024)

    def start(self):
        command = [os.path.join(script_abspath, self.script)]

        env = os.environ.copy()
        env['TARANTOOL_CONSOLE_SOCK'] = self.console_sock

        with open(os.devnull, 'w') as FNULL:
            self.process = Popen(command, env=env, stdout=FNULL, stderr=FNULL)

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

    def eval(self, func_body):
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

        cmd = '''
            local ok, ret = pcall(function()
                local function f()
                    {}
                end
                return f()
            end)
            ret = require("json").encode({{
                ok = ok,
                ret = ret ~= nil and ret or box.NULL,
            }})
            return string.hex(ret)
        '''.format(func_body)

        lines = [line.strip() for line in cmd.split('\n') if line.strip()]
        cmd = ' '.join(lines) + '\n'

        sendall(cmd)

        raw_output = recvall()

        hex_output = re.sub(r"^---\n-\s+?", '', raw_output)
        hex_output = re.sub(r"'?\n...\n$", '', hex_output)
        hex_output = re.sub(r"\n\s*", '', hex_output)

        try:
            output = bytearray.fromhex(hex_output).decode('utf-8')
        except Exception:
            raise Exception(hex_output)

        ret = json.loads(output)
        if not ret['ok']:
            errmsg = 'Error while running function: {}. (Function: {})'.format(ret['ret'], func_body)
            raise Exception(errmsg)

        return ret['ret']

    def stop(self):
        self.sock.close()
        if self.process is not None:
            self.process.kill()
            self.process.communicate()

    def write_file(self, path, content=''):
        os.path.exists.set_exists(path)
        self.eval('''
            require('fio').path.write_file({{
                path = '{}',
                content = '{}',
            }})
        '''.format(path, content))

    def remove_file(self, path):
        os.path.exists.set_not_exists(path)
        self.eval('''
            require('fio').path.remove_file('{}')
        '''.format(path))

    def set_instance_config(self, config,
                            instance_conf_file=None,
                            conf_section_name=None):
        if instance_conf_file is None:
            instance_conf_file = Instance.INSTANCE_CONF_PATH

        if conf_section_name is None:
            conf_section_name = Instance.CONF_SECTION

        params = ', '.join([
            '{}: {}'.format(k, v)
            for k, v in config.items()
        ])
        conf = '{conf_section_name}: {{ {params} }}'.format(
            conf_section_name=conf_section_name,
            params=params
        )
        self.write_file(instance_conf_file, conf)

    def set_app_config(self, config):
        config = config.copy()
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
        self.eval('''
            require('cartridge').internal.set_box_cfg_function({})
        '''.format('true' if value else 'false'))

    def set_cartridge_version(self, version):
        self.eval('''
            require('cartridge').VERSION = '{}'
        '''.format(version))

    def set_fail_on(self, func, value=True):
        self.eval('''
            require('cartridge').internal.set_fail('{func}', {value})
        '''.format(
            func=func,
            value='true' if value else 'false'
        ))

    def clear_calls(self, func):
        self.eval('''
            require('cartridge').internal.clear_calls('{func}')
        '''.format(func=func))

    def get_calls(self, func):
        return self.eval('''
            return require('cartridge').internal.get_calls('{func}')
        '''.format(func=func))

    def set_variable(self, name, value):
        self.eval('''
            local value = require('json').decode('{encoded_value}')
            require('cartridge').internal.set_variable('{name}', value)
        '''.format(
            name=name,
            encoded_value=json.dumps(value)
        ))

    def set_box_cfg(self, new_box_cfg):
        self.eval('''
            local value = require('json').decode('{encoded_value}')
            require('cartridge').internal.set_box_cfg(value)
        '''.format(
            encoded_value=json.dumps(new_box_cfg)
        ))

    def add_topology_servers(self, servers):
        for s in servers:
            s_replicaset = '{{ alias = "{alias}", uuid = "{uuid}", roles = {roles} }}'.format(
                alias=s['replicaset']['alias'],
                uuid=s['replicaset']['uuid'],
                roles='{{ {} }}'.format(', '.join([
                    '"{}"'.format(role) for role in s['replicaset']['roles']
                ]))
            )

            self.eval('''
                require('cartridge').internal.add_topology_server({{
                    uuid = '{uuid}',
                    uri = '{uri}',
                    alias = '{alias}',
                    status = '{status}',
                    replicaset = {replicaset}
                }})
            '''.format(
                uuid=s['uuid'],
                uri=s['uri'],
                alias=s['alias'],
                status=s.get('status', 'healthy'),
                replicaset=s_replicaset
            ))

    def add_topology_replicaset(self, r):
        r_servers = '{{ {} }}'.format(
            ', '.join([
                "{{ alias = '{}', priority = {} }}".format(s['alias'], s['priority'])
                for s in r['servers']
            ])
        )

        weight = 'nil'
        if 'weight' in r and r['weight'] is not None:
            weight = r['weight']

        vshard_group = 'nil'
        if 'vshard_group' in r and r['vshard_group'] is not None:
            vshard_group = "'%s'" % r['vshard_group']

        all_rw = 'nil'
        if 'all_rw' in r and r['all_rw'] is not None:
            all_rw = 'true' if r['all_rw'] else 'false'

        self.eval('''
            require('cartridge').internal.add_topology_replicaset({{
                uuid = '{uuid}',
                alias = '{alias}',
                status = '{status}',
                roles = {roles},
                weight = {weight},
                all_rw = {all_rw},
                vshard_group = {vshard_group},
                servers = {servers},
            }})
        '''.format(
            uuid=r['uuid'],
            alias=r['alias'],
            status=r.get('status', 'healthy'),
            roles='{{ {} }}'.format(', '.join([
                '"{}"'.format(role) for role in r['roles']
            ])),
            weight=weight,
            all_rw=all_rw,
            vshard_group=vshard_group,
            servers=r_servers
        ))

    def add_unjoined_server(self, alias, uri, status='healthy'):
        self.eval('''
            require('cartridge').internal.add_unjoined_server({{
                uri = '{uri}',
                alias = '{alias}',
                status = '{status}',
            }})
        '''.format(
            uri=uri,
            alias=alias,
            status=status,
        ))
