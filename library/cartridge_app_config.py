#!/usr/bin/python

import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.helpers import ModuleRes
from ansible.module_utils.helpers import get_authorized_session


argument_spec = {
    'app_config': {'required': True, 'type': 'dict'},
    'control_instance_address': {'required': True, 'type': 'str'},
    'control_instance_port': {'required': True, 'type': 'str'},
    'cluster_cookie': {'required': True, 'type': 'str'},
}


def section_is_deleted(section):
    return 'deleted' in section and section['deleted'] is True


def config_app(params):
    config_url = 'http://{}:{}/admin/config'.format(
        params['control_instance_address'],
        params['control_instance_port']
    )

    session = get_authorized_session(params['cluster_cookie'])

    # Get current config
    response = session.get(config_url)
    if response.status_code != 200:
        return ModuleRes(success=False, msg='Failed to get current config')

    current_config = yaml.safe_load(response.content)
    if not current_config:
        current_config = {}  # be sure it's dict, not list
    config = params['app_config']

    # Patch it
    changed = False

    for section_name, section in config.items():
        if section_is_deleted(section):
            if section_name in current_config:
                del current_config[section_name]
                changed = True
        else:
            if section_name not in current_config or current_config[section_name] != section['body']:
                current_config[section_name] = section['body']
                changed = True

    # Put it to cluster
    response = session.put(config_url, data=yaml.safe_dump(current_config))
    if response.status_code != 200:
        return ModuleRes(success=False, msg='Failed to put config')

    return ModuleRes(success=True, changed=changed)


def main():
    module = AnsibleModule(argument_spec=argument_spec)
    res = config_app(module.params)

    if res.success is True:
        module.exit_json(changed=res.changed, meta=res.meta)
    else:
        module.fail_json(msg=res.msg)


if __name__ == '__main__':
    main()
