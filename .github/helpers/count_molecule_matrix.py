#!/usb/bin/env python3

import argparse
import json


def get_matrix_base(molecule_scenario=None, ansible_version=None):
    return {
        'molecule_scenario': molecule_scenario or 'default',
        'ansible_version': ansible_version or '2.8.0',
    }


def get_molecule_command(molecule_command=None):
    return molecule_command or 'test'


def get_ce_params(molecule_scenario=None, ansible_version=None, tarantool_version=None, molecule_command=None):
    return {
        **get_matrix_base(molecule_scenario, ansible_version),
        'tarantool_version': tarantool_version or '2.6',
        'molecule_command': get_molecule_command(molecule_command),
    }


def get_ee_params(molecule_scenario=None, ansible_version=None, sdk_version=None, molecule_command=None):
    return {
        **get_matrix_base(molecule_scenario, ansible_version),
        'sdk_version': sdk_version or '2.6.2-124-g2c3b91439-r391',
        'molecule_command': get_molecule_command(molecule_command),
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
        ce_matrix.append(get_ce_params(molecule_scenario='eval'))
        ce_matrix.append(get_ce_params(molecule_scenario='start_stop'))
        ce_matrix.append(get_ce_params(molecule_scenario='dead_instances'))

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
