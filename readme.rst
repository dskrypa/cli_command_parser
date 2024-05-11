CLI Command Parser
##################

|downloads| |py_version| |coverage_badge| |build_status| |Ruff|

.. |py_version| image:: https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20-blue
    :target: https://pypi.org/project/cli-command-parser/

.. |coverage_badge| image:: https://codecov.io/gh/dskrypa/cli_command_parser/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/dskrypa/cli_command_parser

.. |build_status| image:: https://github.com/dskrypa/cli_command_parser/actions/workflows/run-tests.yml/badge.svg
    :target: https://github.com/dskrypa/cli_command_parser/actions/workflows/run-tests.yml

.. |Ruff| image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
    :target: https://docs.astral.sh/ruff/

.. |downloads| image:: https://img.shields.io/pypi/dm/cli-command-parser
    :target: https://pypistats.org/packages/cli-command-parser


CLI Command Parser is a class-based CLI argument parser that defines parameters with descriptors.  It provides the
tools to quickly and easily get started with basic CLIs, and it scales well to support even very large and complex
CLIs while remaining readable and easy to maintain.

The primary goals of this project:
  - Make it easy to define subcommands and actions in an clean and organized manner
  - Allow for inheritance so that common parameters don't need to be repeated
  - Make it easy to handle common initialization tasks for all actions / subcommands once
  - Reduce the amount of boilerplate code that is necessary for setting up parsing and handling argument values


Example Program
***************

.. code-block:: python

    from cli_command_parser import Command, Option, main

    class Hello(Command, description='Simple greeting example'):
        name = Option('-n', default='World', help='The person to say hello to')
        count: int = Option('-c', default=1, help='Number of times to repeat the message')

        def main(self):
            for _ in range(self.count):
                print(f'Hello {self.name}!')

    if __name__ == '__main__':
        main()


.. code-block:: shell-session

    $ hello_world.py --name Bob -c 3
    Hello Bob!
    Hello Bob!
    Hello Bob!

    $ hello_world.py -h
    usage: hello_world.py [--name NAME] [--count COUNT] [--help]

    Simple greeting example

    Optional arguments:
      --name NAME, -n NAME        The person to say hello to (default: 'World')
      --count COUNT, -c COUNT     Number of times to repeat the message (default: 1)
      --help, -h                  Show this help message and exit


Installing CLI Command Parser
*****************************

CLI Command Parser can be installed and updated via `pip <https://pip.pypa.io/en/stable/getting-started/>`__::

    $ pip install -U cli-command-parser


There are no required dependencies.  Support for formatting wide characters correctly in help text descriptions can
be included by adding `wcwidth <https://wcwidth.readthedocs.io>`__ to your project's requirements, and/or by installing
with optional dependencies::

    $ pip install -U cli-command-parser[wcwidth]


Python Version Compatibility
============================

Python versions 3.8 and above are currently supported.  The last release of CLI Command Parser that supported 3.7 was
2023-04-30.  Support for Python 3.7 `officially ended on 2023-06-27 <https://devguide.python.org/versions/>`__.

When using Python 3.8, some additional packages that backport functionality that was added in later Python versions
are required for compatibility.

To use the argparse to cli-command-parser conversion script with Python 3.8, there is a dependency on
`astunparse <https://astunparse.readthedocs.io>`__.  If you are using Python 3.9 or above, then ``astunparse`` is not
necessary because the relevant code was added to the stdlib ``ast`` module.  If you're unsure, you can install
cli-command-parser with the following command to automatically handle whether that extra dependency is needed or not::

    $ pip install -U cli-command-parser[conversion]


Links
*****

- Documentation: https://dskrypa.github.io/cli_command_parser/
- Example Scripts: https://github.com/dskrypa/cli_command_parser/tree/main/examples
- PyPI Releases: https://pypi.org/project/cli-command-parser/
- Source Code: https://github.com/dskrypa/cli_command_parser
- Issue Tracker: https://github.com/dskrypa/cli_command_parser/issues
