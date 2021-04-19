#!/usb/bin/env python3

import argparse
import json


def get_matrix_base(ansible_version=None, molecule_command=None, molecule_scenario=None):
    return {
        'ansible_version': ansible_version or '2.8.0',
        'molecule_command': molecule_command or 'test',
        'molecule_scenario': molecule_scenario or 'default',
    }


def get_ce_params(tarantool_version=None, ansible_version=None, molecule_command=None, molecule_scenario=None):
    return {
        **get_matrix_base(ansible_version, molecule_command, molecule_scenario),
        'tarantool_version': tarantool_version or '2.6',
    }


def get_ee_params(sdk_version=None, ansible_version=None, molecule_command=None, molecule_scenario=None):
    return {
        **get_matrix_base(ansible_version, molecule_command, molecule_scenario),
        'sdk_version': sdk_version or '2.6.2-124-g2c3b91439-r391',
    }


def main(event_name, repo_owner, review_state, ref):
    ce_matrix = []
    ee_matrix = []

    if event_name == 'push' or event_name == 'pull_request' and repo_owner != 'tarantool':
        ce_matrix.append(get_ce_params())

    if event_name == 'workflow_dispatch' or review_state == 'approved' or ref == 'refs/heads/master':
        ce_matrix.append(get_ce_params(molecule_scenario='tasks_from'))
        ce_matrix.append(get_ce_params(molecule_scenario='update_cartridge'))
        ce_matrix.append(get_ce_params(molecule_scenario='check_facts'))
        ce_matrix.append(get_ce_params(molecule_scenario='rolling_update'))
        ce_matrix.append(get_ce_params(molecule_scenario='needs_restart'))
        ce_matrix.append(get_ce_params(molecule_scenario='package_name'))

        ce_matrix.append(get_ce_params(tarantool_version='1.10'))

        ce_matrix.append(get_ce_params(ansible_version='2.9.0'))
        ce_matrix.append(get_ce_params(ansible_version='2.10.0'))
        # TODO: Uncomment after fixing the check mode
        # ce_matrix.append(get_ce_version(molecule_command='check'))

        ee_matrix.append(get_ee_params(sdk_version='2.6.2-124-g2c3b91439-r391'))

    print(f'::set-output name=ce-tests-found::{"true" if len(ce_matrix) > 0 else "false"}')
    print(f'::set-output name=ee-tests-found::{"true" if len(ee_matrix) > 0 else "false"}')

    print(f'::set-output name=ce-matrix::{json.dumps({"include": ce_matrix})}')
    print(f'::set-output name=ee-matrix::{json.dumps({"include": ee_matrix})}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Count matrix for Molecule tests.')
    parser.add_argument('--event_name', type=str, help='name of GitHub event')
    parser.add_argument('--repo_owner', type=str, help='owner of code')
    parser.add_argument('--review_state', type=str, help='state of review')
    parser.add_argument('--ref', type=str, help='ref that was pushed')
    args = parser.parse_args()
    main(args.event_name, args.repo_owner, args.review_state, args.ref)
