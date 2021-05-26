from importlib.machinery import SourceFileLoader
utils = SourceFileLoader("utils", "./molecule/common/tests/utils.py").load_module()


testinfra_hosts = utils.get_testinfra_hosts()


def test_cluster_is_healthy():
    admin_api_url = utils.get_admin_api_url()

    # Get all started instances
    query = '''
        query {
          replicasets {
            status
          }
        }
    '''
    session = utils.get_authorized_session()
    response = session.post(admin_api_url, json={'query': query})
    assert response.status_code == 200

    replicasets = response.json()['data']['replicasets']
    assert all([r['status'] == 'healthy' for r in replicasets])
