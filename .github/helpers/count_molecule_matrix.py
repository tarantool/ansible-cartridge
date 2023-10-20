#!/usb/bin/env python3

import argparse
import json
import os

#############
# CONSTANTS #
#############

MOLECULE_SCENARIOS_PATH = './molecule'
DEFAULT_SCENARIO = 'default'
IGNORED_PATHS = [
    'common',
]

DEFAULT_MOLECULE_COMMAND = 'test'
NOT_DEFAULT_MOLECULE_COMMANDS = [
    # TODO: Uncomment after fixing the check mode
    # 'check'
]

DEFAULT_ANSIBLE_VERSION = '6.5.0'
NOT_DEFAULT_ANSIBLE_VERSIONS = [
    '8.5.0',
]

DEFAULT_PYTHON_VERSION = '3.9'

DEFAULT_TARANTOOL_VERSION = '2'

DEFAULT_SDK_VERSION = '2.8.4-0-r553'
NOT_DEFAULT_SDK_VERSIONS = []

######################
# MATRIX CALCULATION #
######################


def get_version_list(version):
    return list(map(lambda x: int(x), version.split('.')))


def compare_versions(version_1, version_2):
    v1_list = get_version_list(version_1)
    v2_list = get_version_list(version_2)
    if v1_list > v2_list:
        return 1
    elif v1_list == v2_list:
        return 0
    else:
        return -1


def get_matrix_base(molecule_scenario=None, ansible_version=None, python_version=None):
    return {
        'molecule_scenario': molecule_scenario or DEFAULT_SCENARIO,
        'ansible_version': ansible_version or DEFAULT_ANSIBLE_VERSION,
        'python_version': python_version or DEFAULT_PYTHON_VERSION,
    }


def get_ce_params(
    molecule_scenario=None, ansible_version=None, python_version=None,
    tarantool_version=None, molecule_command=None,
):
    matrix = get_matrix_base(molecule_scenario, ansible_version, python_version)
    matrix.update(
        tarantool_version=tarantool_version or DEFAULT_TARANTOOL_VERSION,
        molecule_command=molecule_command or DEFAULT_MOLECULE_COMMAND,
    )
    return matrix


def get_ee_params(
    molecule_scenario=None, ansible_version=None, python_version=None,
    sdk_version=None, molecule_command=None,
):
    matrix = get_matrix_base(molecule_scenario, ansible_version, python_version)
    matrix.update(
        sdk_version=sdk_version or DEFAULT_SDK_VERSION,
        molecule_command=molecule_command or DEFAULT_MOLECULE_COMMAND,
    )
    return matrix


def main(event_name, repo_owner, review_state, ref):
    ce_matrix = []
    ee_matrix = []

    if any([
        event_name == 'push',
        event_name == 'pull_request' and repo_owner != 'tarantool',
        event_name == 'workflow_dispatch',
        # review_state == 'approved',
        # ref == 'refs/heads/master',
    ]):
        ce_matrix.append(get_ce_params())

        ee_matrix.append(get_ee_params())

        all_scenarios = sorted(os.listdir(MOLECULE_SCENARIOS_PATH))
        scenarios_to_skip = [DEFAULT_SCENARIO] + IGNORED_PATHS
        for name in filter(lambda scenario: scenario not in scenarios_to_skip, all_scenarios):
            ce_matrix.append(get_ce_params(molecule_scenario=name))

        for command in NOT_DEFAULT_MOLECULE_COMMANDS:
            ce_matrix.append(get_ce_params(molecule_command=command))

        for ansible_version in NOT_DEFAULT_ANSIBLE_VERSIONS:
            python_version = None
            if compare_versions(ansible_version, '6.5.0') >= 0:
                python_version = '3.11'
            ce_matrix.append(get_ce_params(ansible_version=ansible_version, python_version=python_version))

        for sdk_version in NOT_DEFAULT_SDK_VERSIONS:
            ee_matrix.append(get_ee_params(sdk_version=sdk_version))

    print('::set-output name=ce-tests-found::' + "true" if len(ce_matrix) > 0 else "false")
    print('::set-output name=ee-tests-found::' + "true" if len(ee_matrix) > 0 else "false")

    print('::set-output name=ce-matrix::' + json.dumps({"include": ce_matrix}))
    print('::set-output name=ee-matrix::' + json.dumps({"include": ee_matrix}))

    print('Computed matrices:')
    print(json.dumps({
        'ce-matrix': ce_matrix,
        'ee-matrix': ee_matrix,
    }, indent=4))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Count matrix for Molecule tests.')
    parser.add_argument('--event_name', type=str, help='name of GitHub event')
    parser.add_argument('--repo_owner', type=str, help='owner of code')
    parser.add_argument('--review_state', type=str, help='state of review')
    parser.add_argument('--ref', type=str, help='ref that was pushed')
    args = parser.parse_args()
    main(args.event_name, args.repo_owner, args.review_state, args.ref)
