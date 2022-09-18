CLI Command Parser
##################

|downloads| |py_version| |coverage_badge| |build_status| |Blue|

.. |py_version| image:: https://img.shields.io/badge/python-3.7%20%7C%203.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20-blue
    :target: https://pypi.org/project/cli-command-parser/

.. |coverage_badge| image:: https://codecov.io/gh/dskrypa/cli_command_parser/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/dskrypa/cli_command_parser

.. |build_status| image:: https://github.com/dskrypa/cli_command_parser/actions/workflows/run-tests.yml/badge.svg
    :target: https://github.com/dskrypa/cli_command_parser/actions/workflows/run-tests.yml

.. |Blue| image:: https://img.shields.io/badge/code%20style-blue-blue.svg
    :target: https://blue.readthedocs.io/

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
      --help, -h                  Show this help message and exit (default: False)


Installing CLI Command Parser
*****************************

CLI Command Parser can be installed and updated via `pip <https://pip.pypa.io/en/stable/getting-started/>`__::

    $ pip install -U cli-command-parser


There are no required dependencies.  Support for formatting wide characters correctly in help text descriptions can
be included by adding `wcwidth <https://wcwidth.readthedocs.io>`__ to your project's requirements, and/or by installing
with optional dependencies::

    $ pip install -U cli-command-parser[wcwidth]


User Guide
**********

Building Commands
=================

:doc:`intro`
    Introduction to Commands, Parameters, and main functions.

:doc:`commands`
    Explanation of special Command methods and Command inheritance.

:doc:`parameters`
    Introduces each Parameter type and their supported options.

:doc:`groups`
    How to group Parameters for help text organization or to enforce or prevent Parameter combinations.

:doc:`subcommands`
    How to define, use, and customize subcommands.

:doc:`inputs`
    Custom input types.


Configuring & Documenting Commands
==================================

:doc:`configuration`
    Configuration options for parsing, help text formatting, and more.

:doc:`documentation`
    How to generate and customize documentation and help text.

:doc:`examples`
    Automatically generated documentation for the :gh_proj_url:`example scripts <tree/main/examples>` in this project.


Advanced
========

:doc:`advanced`
    Advanced usage patterns.

:doc:`testing`
    How to unit test Commands.

:doc:`api`
    Lower level API documentation.


Links
*****

- Documentation: https://dskrypa.github.io/cli_command_parser/
- Example Scripts: https://github.com/dskrypa/cli_command_parser/tree/main/examples
- PyPI Releases: https://pypi.org/project/cli-command-parser/
- Source Code: https://github.com/dskrypa/cli_command_parser
- Issue Tracker: https://github.com/dskrypa/cli_command_parser/issues


Indices and Tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. Table of Contents (navigation)

.. toctree::
   :caption: User Guide
   :maxdepth: 3
   :hidden:

   intro
   commands
   parameters
   groups
   subcommands
   inputs
   configuration
   documentation
   advanced
   testing

.. toctree::
   :caption: API Documentation
   :maxdepth: 4
   :hidden:

   api

.. toctree::
   :caption: Example Script Docs
   :maxdepth: 2
   :hidden:

   examples
