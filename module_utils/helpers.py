#!/usr/bin/python

import requests
import time

class ModuleRes:
    def __init__(self, success, msg=None, changed=False, meta=None):
        self.success = success
        self.msg = msg
        self.changed = changed
        self.meta = meta


def list_to_graphql_string(l):
    return '[{}]'.format(', '.join(['"{}"'.format(i) for i in l]))


def check_query(query, response):
    if response.status_code != 200:
        return False, ModuleRes(success=False,
                         msg="Query failed to run by returning code of {}. {}".format(response.status_code, query))
    if 'errors' in response.json():
        return False, ModuleRes(success=False,
                          msg="Query failed to run with error {}. {}".format(response.json()['errors'][0]['message'], query))

    return True, None


__authorized_session = None

def get_authorized_session(cluster_cookie):
  global __authorized_session
  if __authorized_session is None:
    __authorized_session = requests.Session()
    __authorized_session.auth = ('admin', cluster_cookie)

  return __authorized_session


def get_all_instances_info(control_instance_admin_api_url, session):
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

    response = session.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return False, err

    instances = response.json()['data']['servers']
    return True, instances


def get_instance_info(instance_admin_api_url, control_instance_admin_api_url, session):
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

    response = session.post(instance_admin_api_url, json={'query': query})
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
              alias
              roles
            }}
          }}
        }}
    '''.format(instance_uuid)

    response = session.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return False, err

    instance = response.json()['data']['servers'][0]
    return True, instance


def get_replicaset_info(control_instance_admin_api_url, session, name):
    # Get all replicasets
    query = '''
        query {
          replicasets {
            uuid
            alias
            status
            roles
            master {
              alias
            }
            servers {
              alias
            }
          }
        }
    '''

    response = session.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return False, err

    replicasets = response.json()['data']['replicasets']

    # Find by name
    for replicaset in replicasets:
        if replicaset['alias'] == name:
            return True, replicaset

    return True, None


def wait_for_replicaset_is_healthy(control_instance_admin_api_url, session, replicaset_name):
    delay = 0.5
    timeout = 5
    while True:
        time_start = time.time()
        now = time.time()
        if now > time_start + timeout:
            return False

        ok, replicaset_info = get_replicaset_info(
            control_instance_admin_api_url,
            session,
            replicaset_name
        )
        if ok and replicaset_info['status'] == 'healthy':
            return True

        time.sleep(delay)
