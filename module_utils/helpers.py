#!/usr/bin/python

import requests

class ModuleRes:
    def __init__(self, success, msg=None, changed=False, meta=None):
        self.success = success
        self.msg = msg
        self.changed = changed
        self.meta = meta


def check_query(query, response):
    if response.status_code != 200:
        return False, ModuleRes(success=False,
                         msg="Query failed to run by returning code of {}. {}".format(response.status_code, query))
    if 'errors' in response.json():
        return False, ModuleRes(success=False,
                          msg="Query failed to run with error {}. {}".format(response.json()['errors'][0]['message'], query))

    return True, None


def get_all_instances_info(control_instance_address, control_instance_port):
    control_instance_admin_api_url = 'http://{}:{}/admin/api'.format(
        control_instance_address,
        control_instance_port
    )

    # Get all instances info from control server
    query = '''
        query {
          servers {
            uri
            alias
            status
            replicaset {
              uuid
            }
          }
        }
    '''

    response = requests.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return False, err

    instances = response.json()['data']['servers']
    return True, instances


def get_instance_info(instance_address, instance_port, control_instance_address, control_instance_port):
    instance_admin_api_url = 'http://{}:{}/admin/api'.format(
        instance_address,
        instance_port
    )
    control_instance_admin_api_url = 'http://{}:{}/admin/api'.format(
        control_instance_address,
        control_instance_port
    )

    # Get instance UUID
    query = '''
        query {
          cluster {
            self {
              uuid
              uri
            }
          }
        }
    '''

    response = requests.post(instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return False, err

    instance_uuid = response.json()['data']['cluster']['self']['uuid']
    if instance_uuid is None:
        # Instance is not joined yet
        return True, response.json()['data']['cluster']['self']

    # Get more instance info from control server
    query = '''
        query {{
          servers(uuid: "{}") {{
            uuid
            uri
            alias
            status
            replicaset {{
              uuid
              roles
            }}
          }}
        }}
    '''.format(instance_uuid)

    response = requests.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return False, err

    instance = response.json()['data']['servers'][0]
    return True, instance
