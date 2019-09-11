#!/usr/bin/python

class ModuleRes:
    def __init__(self, success, msg=None, changed=False, meta=None):
        self.success = success
        self.msg = msg
        self.changed = changed
        self.meta = meta


def check_query_error(query, response):
    if response.status_code != 200:
        return ModuleRes(success=False,
                         msg="Query failed to run by returning code of {}. {}".format(response.status_code, query))

    if 'errors' in response.json():
        return ModuleRes(success=False,
                          msg="Query failed to run with error {}. {}".format(response.json()['errors'][0]['message'], query))

    return None
