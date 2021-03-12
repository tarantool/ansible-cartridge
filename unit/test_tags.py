import unittest
from pathlib import Path

from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.block import Block
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
        import_block = self.play.get_tasks()[0][0]

        def get_block_tasks(block: Block):
            tasks = []
            block = block.filter_tagged_tasks(self.all_vars)
            block_tasks = block.block + block.rescue + block.always
            for block_task in block_tasks:
                if isinstance(block_task, Block):
                    tasks += get_block_tasks(block_task)
                else:
                    tasks.append(block_task)
            return tasks

        names = []
        for task in get_block_tasks(import_block):
            _, name = task.get_name().split(' : ', maxsplit=1)
            names.append(name)
        return names

    def test_without_tags(self):
        names = self.get_tasks_by_tags({})
        self.assertEqual(names, [
            'Validate config',
            'Validate OS Family',
            "Set 'remote_user' for delegated tasks",
            'Collect instance info',
            'Select one instance for each physical machine',
            'Select one not expelled instance',
            'Collect scenario steps',
            'Include steps by scenario',
        ])

    def test_tag_cartridge_instances(self):
        names = self.get_tasks_by_tags({'cartridge-instances'})
        self.assertEqual(names, [
            'Validate config',
            'Validate OS Family',
            "Set 'remote_user' for delegated tasks",
            'Collect instance info',
            'Select one instance for each physical machine',
            'Select one not expelled instance',
            'Collect scenario steps',
            'Include steps by scenario',
        ])

    def test_tag_cartridge_replicasets(self):
        names = self.get_tasks_by_tags({'cartridge-replicasets'})
        self.assertEqual(names, [
            'Validate config',
            'Validate OS Family',
            "Set 'remote_user' for delegated tasks",
            'Collect instance info',
            'Select one instance for each physical machine',
            'Select one not expelled instance',
            'Collect scenario steps',
            'Include steps by scenario',
        ])

    def test_tag_cartridge_config(self):
        names = self.get_tasks_by_tags({'cartridge-config'})
        self.assertEqual(names, [
            'Validate config',
            'Validate OS Family',
            "Set 'remote_user' for delegated tasks",
            'Collect instance info',
            'Select one instance for each physical machine',
            'Select one not expelled instance',
            'Collect scenario steps',
            'Include steps by scenario',
        ])

    def test_not_cartridge_tag(self):
        names = self.get_tasks_by_tags({'test'})
        self.assertEqual(names, [])
