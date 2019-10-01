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


def boolean_to_graphql_string(p):
    return 'true' if p else 'false'


def check_query(query, response):
    if response.status_code != 200:
        return False, ModuleRes(
            success=False,
            msg="Query failed to run by returning code of {}. {}".format(response.status_code, query)
        )
    if 'errors' in response.json():
        return False, ModuleRes(
            success=False,
            msg="Query failed to run with error {}. {}".format(response.json()['errors'][0]['message'], query)
        )

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


def get_cluster_auth_params(control_instance_admin_api_url, session):
    query = '''
        query {
            cluster {
                auth_params {
                    enabled
                    cookie_max_age
                    cookie_renew_age
                }
            }
        }
    '''

    response = session.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return False, err

    cluster_auth_params = response.json()['data']['cluster']['auth_params']
    return True, cluster_auth_params


def edit_cluster_auth_params(control_instance_admin_api_url, session,
                             enabled=None, cookie_max_age=None, cookie_renew_age=None):
    auth_query_params = []

    if enabled is not None:
        auth_query_params.append('enabled: {}'.format(boolean_to_graphql_string(enabled)))

    if cookie_max_age is not None:
        auth_query_params.append('cookie_max_age: {}'.format(cookie_max_age))

    if cookie_renew_age is not None:
        auth_query_params.append('cookie_renew_age: {}'.format(cookie_renew_age))

    query = '''
        mutation {{
            cluster {{
                auth_params({}) {{
                    enabled
                    cookie_max_age
                    cookie_renew_age
                }}
            }}
        }}
    '''.format(', '.join(auth_query_params))
    response = session.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return False, err

    new_cluster_auth_params = response.json()['data']['cluster']['auth_params']
    return True, new_cluster_auth_params


def check_cluster_auth_implements_all(control_instance_admin_api_url, session):
    query = '''
        query {
            cluster {
                auth_params {
                    implements_list_users
                    implements_remove_user
                    implements_add_user
                    implements_edit_user
                    implements_get_user
                    implements_check_password
                }
            }
        }
    '''

    response = session.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return False, err

    cluster_implements = response.json()['data']['cluster']['auth_params']
    not_implemented_list = [k for k, v in cluster_implements.items() if not v]

    if not_implemented_list:
        errmsg = 'Cluster auth backend must implement this operations to allow users management: {}'.format(
            ', '.join([i.replace('implements_', '') for i in not_implemented_list])
        )
        return False, ModuleRes(success=False, msg=errmsg)

    return True, None


def get_cluster_users(control_instance_admin_api_url, session):
    query = '''
        query {
            cluster {
                users {
                    username
                    fullname
                    email
                }
            }
        }
    '''

    response = session.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return False, err

    users = response.json()['data']['cluster']['users']
    return True, users


def add_cluster_user(control_instance_admin_api_url, session, user):
    add_user_params = [
        'username: "{}"'.format(user['username']),
    ]

    if 'password' in user:
        add_user_params.append('password: "{}"'.format(user['password']))

    if 'email' in user:
        add_user_params.append('email: "{}"'.format(user['email']))

    if 'fullname' in user:
        add_user_params.append('fullname: "{}"'.format(user['fullname']))

    query = '''
        mutation {{
            cluster {{
                add_user({}) {{}}
            }}
        }}
    '''.format(', '.join(add_user_params))

    response = session.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return False, err

    return True, None


def delete_cluster_user(control_instance_admin_api_url, session, user):
    query = '''
        mutation {{
            cluster {{
                remove_user(username: "{}") {{}}
            }}
        }}
    '''.format(user['username'])

    response = session.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return False, err

    return True, None


def edit_cluster_user(control_instance_admin_api_url, session, user):
    add_user_params = [
        'username: "{}"'.format(user['username']),
    ]

    if 'password' in user:
        add_user_params.append('password: "{}"'.format(user['password']))

    if 'email' in user:
        add_user_params.append('email: "{}"'.format(user['email']))

    if 'fullname' in user:
        add_user_params.append('fullname: "{}"'.format(user['fullname']))

    query = '''
        mutation {{
            cluster {{
                edit_user({}) {{
                    username
                    fullname
                    email
                }}
            }}
        }}
    '''.format(', '.join(add_user_params))

    response = session.post(control_instance_admin_api_url, json={'query': query})
    ok, err = check_query(query, response)
    if not ok:
        return False, err

    edited_user = response.json()['data']['cluster']['edit_user']

    return True, edited_user
