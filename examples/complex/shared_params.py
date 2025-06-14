"""
Simplified example of subcommands with common shared Parameters in a parent subclass that does not get registered as a
subcommand choice.

:author: Doug Skrypa
"""

import logging
from abc import ABC

from cli_command_parser import Flag, Option, ParamGroup, SubCommand

from .base import Example

log = logging.getLogger(__name__)

ITEMS = {
    'user': ('user_a', 'user_b', 'user_c'),
    'group': {'a': ('user_a', 'user_b'), 'b': ('user_b', 'user_c')},
    'foo': ('a', 'b', 'c', 'd'),
    'bar': ('1', '2', '3', '4', '5'),
}


class Update(Example):
    item_type = SubCommand(local_choices=('foo', 'bar'), help='The type of item to update')
    dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')
    with ParamGroup(mutually_exclusive=True):
        ids = Option('-i', metavar='ID', nargs='+', help='The IDs of the item to update')
        all = Flag('-A', help='Update all items')
    with ParamGroup('Common Fields'):
        name = Option('-n', help='The new name for the specified item(s)')
        description = Option('-d', help='The new description to use for the specified item(s)')

    def main(self):
        updates = self.get_updates()
        if not updates:
            print('No updates selected')
            return

        items = self.get_items()
        if not items:
            print(f'No {self.item_type}s found for the specified criteria')
            return

        prefix = '[DRY RUN] Would update' if self.dry_run else 'Updating'
        for item in items:
            print(f'{prefix} {item}: {updates}')

    def get_updates(self):
        updates = {}
        if self.name:
            updates['name'] = self.name
        if self.description:
            updates['description'] = self.description
        return updates

    def get_items(self):
        items = ITEMS[self.item_type]
        if self.all:
            return items
        return [item_id for item_id in self.ids if item_id in items]


class UpdateUserOrGroup(Update, ABC):
    """Common parameters for updating users or groups"""

    location = Option('-L', help='The new location for the specified item(s)')


class UpdateUser(UpdateUserOrGroup, choice='user'):
    role = Option('-r', choices=('admin', 'user'), help='The new role for the specified user(s)')

    def get_updates(self):
        updates = super().get_updates()
        if self.role:
            updates['role'] = self.role
        return updates


class UpdateGroup(UpdateUserOrGroup, choice='group'):
    add = Option('-a', metavar='MEMBER', nargs='+', help='Members to add')
    remove = Option('-r', metavar='MEMBER', nargs='+', help='Members to remove')

    def get_updates(self):
        updates = super().get_updates()
        if self.add:
            updates['add'] = self.add
        if self.remove:
            updates['add'] = self.remove
        return updates
