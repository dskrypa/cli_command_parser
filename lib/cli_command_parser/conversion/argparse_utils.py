"""
Typing helpers to make it easier to use Signature.from_callable for automatic conversion of positional to keyword args.
"""

from argparse import ArgumentParser as _ArgumentParser, _SubParsersAction  # noqa

__all__ = ['ArgumentParser', 'SubParsersAction']


class ArgumentParser(_ArgumentParser):
    def add_argument_group(
        self, title=None, description=None, *, prefix_chars=None, argument_default=None, conflict_handler=None
    ):
        kwargs = {k: v for k, v in locals().items() if k not in {'self', '__class__'} and v is not None}
        return super().add_argument_group(**kwargs)

    def add_mutually_exclusive_group(self, *, required=False):
        return super().add_mutually_exclusive_group(required=required)

    # fmt: off
    def add_subparsers(
        self, *, title=None, description=None, prog=None, dest=None, help=None,  # noqa
        action=None, option_string=None, required=None, metavar=None,
    ):
        kwargs = {k: v for k, v in locals().items() if k not in {'self', '__class__'} and v is not None}
        return super().add_subparsers(**kwargs)
    # fmt: on


class SubParsersAction(_SubParsersAction):
    def add_parser(self, name, *, aliases=(), description=None, prog=None, help=None):  # noqa
        return super().add_parser(name, aliases=aliases, description=description, prog=prog, help=help)
