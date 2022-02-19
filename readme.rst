Command Parser
==============

|py_version| |coverage_badge| |build_status| |Black|

.. |py_version| image:: https://img.shields.io/badge/python-3.9%20%7C%203.10%20-blue

.. |coverage_badge| image:: https://codecov.io/gh/dskrypa/command_parser/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/dskrypa/command_parser

.. |build_status| image:: https://github.com/dskrypa/command_parser/actions/workflows/python-package.yml/badge.svg
    :target: https://github.com/dskrypa/command_parser/actions/workflows/python-package.yml

.. |Black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black


Command Parser is a class-based CLI argument parser that defines parameters with descriptors.

The primary goals of this project:
  - Make it easy to define subcommands and actions in an clean and organized manner
  - Allow for inheritance so that common parameters don't need to be repeated
  - Make it easy to handle common initialization tasks for all actions / subcommands once
  - Reduce the amount of boilerplate code that is necessary for setting up parsing and handling argument values


This project is still a work in progress.