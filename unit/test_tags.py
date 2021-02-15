#!/usr/bin/env python3

import unittest
from pathlib import Path

from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.vars.manager import VariableManager


class TestTags(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

        loader = DataLoader()
        inventory = InventoryManager(loader=loader, sources='localhost,')
        variable_manager = VariableManager(loader=loader, inventory=inventory)

        self.play = Play().load({
            'name': "Deploy Cartridge",
            'tasks': [{
                'name': 'Import Cartridge Role',
                'import_role': {
                    'name': str(Path(__file__).parent.parent),
                },
            }],
        }, loader=loader, variable_manager=variable_manager)
        self.all_vars = variable_manager.get_vars(play=self.play)

    def get_tasks_by_tags(self, tags_set):
        self.play.only_tags = tags_set
        tasks = self.play.get_tasks()[0]
        self.assertTrue(len(tasks) == 1, 'Expected one task in playbook with role import!')
        tasks = tasks[0].filter_tagged_tasks(self.all_vars).block

        names = []
        for task in tasks:
            _, name = task.get_name().split(' : ')
            names.append(name)
        return names

    def test_without_tags(self):
        names = self.get_tasks_by_tags({})
        self.assertEqual(names, [
            'Forced facts gathering',
            'Check distribution',
            'Set remote_user for delegated tasks',
            'Validate config',
            'Collect instance info',
            'Get one instance from each physical machine',
            'Install package',
            'Start instance',
            'Restart instances and reload systemd-daemon',
            'Wait for instance to be started',
            'Connect instance to membership',
            'Select one not expelled instance',
            'Select control instance to manage topology and configuration',
            'Edit topology',
            'Cleanup expelled instance files and services',
            'Cartridge auth',
            'Application config',
            'Bootstrap vshard',
            'Wait for instance to be started and buckets are discovered',
            'Manage failover',
        ])

    def test_tag_cartridge_instances(self):
        names = self.get_tasks_by_tags({'cartridge-instances'})
        self.assertEqual(names, [
            'Forced facts gathering',
            'Check distribution',
            'Set remote_user for delegated tasks',
            'Validate config',
            'Collect instance info',
            'Get one instance from each physical machine',
            'Install package',
            'Start instance',
            'Restart instances and reload systemd-daemon',
            'Wait for instance to be started',
            'Connect instance to membership',
        ])

    def test_tag_cartridge_replicasets(self):
        names = self.get_tasks_by_tags({'cartridge-replicasets'})
        self.assertEqual(names, [
            'Forced facts gathering',
            'Check distribution',
            'Set remote_user for delegated tasks',
            'Validate config',
            'Collect instance info',
            # TODO: Remove 'Restart instances and reload systemd-daemon' when Ansible will be updated to 2.11 or higher
            # Ref: https://docs.ansible.com/ansible/latest/collections/ansible/builtin/meta_module.html#notes
            'Restart instances and reload systemd-daemon',
            'Connect instance to membership',
            'Select one not expelled instance',
            'Select control instance to manage topology and configuration',
            'Edit topology',
            'Cleanup expelled instance files and services',
        ])

    def test_tag_cartridge_config(self):
        names = self.get_tasks_by_tags({'cartridge-config'})
        self.assertEqual(names, [
            'Forced facts gathering',
            'Check distribution',
            'Set remote_user for delegated tasks',
            'Validate config',
            'Collect instance info',
            # TODO: Remove 'Restart instances and reload systemd-daemon' when Ansible will be updated to 2.11 or higher
            # Ref: https://docs.ansible.com/ansible/latest/collections/ansible/builtin/meta_module.html#notes
            'Restart instances and reload systemd-daemon',
            'Select one not expelled instance',
            'Select control instance to manage topology and configuration',
            'Cartridge auth',
            'Application config',
            'Bootstrap vshard',
            'Wait for instance to be started and buckets are discovered',
            'Manage failover',
        ])

    def test_not_cartridge_tag(self):
        names = self.get_tasks_by_tags({'test'})
        self.assertEqual(names, [
            # TODO: Remove 'Restart instances and reload systemd-daemon' when Ansible will be updated to 2.11 or higher
            # Ref: https://docs.ansible.com/ansible/latest/collections/ansible/builtin/meta_module.html#notes
            'Restart instances and reload systemd-daemon',
        ])
