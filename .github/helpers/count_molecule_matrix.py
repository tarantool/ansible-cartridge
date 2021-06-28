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

DEFAULT_ANSIBLE_VERSION = '2.8.0'
NOT_DEFAULT_ANSIBLE_VERSIONS = [
    '2.9.0',
    '2.10.0',
    '4.1.0',
]

DEFAULT_TARANTOOL_VERSION = '2.6'
NOT_DEFAULT_TNT_VERSIONS = [
    '1.10'
]

DEFAULT_SDK_VERSION = '2.6.2-124-g2c3b91439-r391'
NOT_DEFAULT_SDK_VERSIONS = []

TDG_SCENARIOS = [
    'config_upload_tdg'
]
DEFAULT_TDG_VERSION = '1.7.7-0-g76c31fca'
TDG_VERSIONS = {
    'config_upload_tdg': [
        # auth-token header; no common.app_version; no admin.upload_config_api;
        '1.6.10-4-g06ea889e',
        # authorization header; no common.app_version; no admin.upload_config_api;
        '1.7.1-0-g92920bea',
        # auth-token header; common.app_version; admin.upload_config_api;
        '1.6.16-0-g7e140c94',
        # authorization header; common.app_version; admin.upload_config_api;
        '1.7.7-0-g76c31fca',
    ],
}


######################
# MATRIX CALCULATION #
######################


def get_matrix_base(molecule_scenario=None, ansible_version=None):
    return {
        'molecule_scenario': molecule_scenario or DEFAULT_SCENARIO,
        'ansible_version': ansible_version or DEFAULT_ANSIBLE_VERSION,
    }


def get_molecule_command(molecule_command=None):
    return molecule_command or DEFAULT_MOLECULE_COMMAND


def get_ce_params(molecule_scenario=None, ansible_version=None, tarantool_version=None, molecule_command=None):
    return {
        **get_matrix_base(molecule_scenario, ansible_version),
        'tarantool_version': tarantool_version or DEFAULT_TARANTOOL_VERSION,
        'molecule_command': get_molecule_command(molecule_command),
    }


def get_ee_params(molecule_scenario=None, ansible_version=None, sdk_version=None, molecule_command=None):
    return {
        **get_matrix_base(molecule_scenario, ansible_version),
        'sdk_version': sdk_version or DEFAULT_SDK_VERSION,
        'molecule_command': get_molecule_command(molecule_command),
    }


def get_tdg_params(molecule_scenario=None, ansible_version=None, tdg_version=None, molecule_command=None):
    return {
        **get_matrix_base(molecule_scenario, ansible_version),
        'tdg_version': tdg_version or DEFAULT_TDG_VERSION,
        'molecule_command': get_molecule_command(molecule_command),
    }


def main(event_name, repo_owner, review_state, ref):
    ce_matrix = []
    ee_matrix = []
    tdg_matrix = []

    if event_name == 'push' or event_name == 'pull_request' and repo_owner != 'tarantool':
        ce_matrix.append(get_ce_params())

    if event_name == 'workflow_dispatch' or review_state == 'approved' or ref == 'refs/heads/master':
        ee_matrix.append(get_ee_params())

        for name in filter(
            lambda scenario:
            scenario != DEFAULT_SCENARIO and scenario not in IGNORED_PATHS and scenario not in TDG_SCENARIOS,
            sorted(os.listdir(MOLECULE_SCENARIOS_PATH)),
        ):
            ce_matrix.append(get_ce_params(molecule_scenario=name))

        for command in NOT_DEFAULT_MOLECULE_COMMANDS:
            ce_matrix.append(get_ce_params(molecule_command=command))

        for version in NOT_DEFAULT_ANSIBLE_VERSIONS:
            ce_matrix.append(get_ce_params(ansible_version=version))

        for version in NOT_DEFAULT_TNT_VERSIONS:
            ce_matrix.append(get_ce_params(tarantool_version=version))

        for version in NOT_DEFAULT_SDK_VERSIONS:
            ee_matrix.append(get_ee_params(sdk_version=version))

        for name in TDG_SCENARIOS:
            for version in TDG_VERSIONS.get(name, [None]):
                tdg_matrix.append(get_tdg_params(molecule_scenario=name, tdg_version=version))

    print(f'::set-output name=ce-tests-found::{"true" if len(ce_matrix) > 0 else "false"}')
    print(f'::set-output name=ee-tests-found::{"true" if len(ee_matrix) > 0 else "false"}')
    print(f'::set-output name=tdg-tests-found::{"true" if len(tdg_matrix) > 0 else "false"}')

    print(f'::set-output name=ce-matrix::{json.dumps({"include": ce_matrix})}')
    print(f'::set-output name=ee-matrix::{json.dumps({"include": ee_matrix})}')
    print(f'::set-output name=tdg-matrix::{json.dumps({"include": tdg_matrix})}')

    print('Computed matrices:')
    print(json.dumps({
        'ce-matrix': ce_matrix,
        'ee-matrix': ee_matrix,
        'tdg-matrix': tdg_matrix,
    }, indent=4))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Count matrix for Molecule tests.')
    parser.add_argument('--event_name', type=str, help='name of GitHub event')
    parser.add_argument('--repo_owner', type=str, help='owner of code')
    parser.add_argument('--review_state', type=str, help='state of review')
    parser.add_argument('--ref', type=str, help='ref that was pushed')
    args = parser.parse_args()
    main(args.event_name, args.repo_owner, args.review_state, args.ref)
