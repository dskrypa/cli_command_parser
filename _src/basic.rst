Getting Started
***************

Installing CLI Command Parser
=============================

CLI Command Parser is available on PyPI::

    $ pip install cli-command-parser


Example
=======

The following is a basic example of a program that uses CLI Command Parser::

    from cli_command_parser import Command, Option, main

    class HelloWorld(Command, description='Simple greeting example'):
        name = Option('-n', default='World', help='The person to say hello to')

        def main(self):
            print(f'Hello {self.name}!')

    if __name__ == '__main__':
        main()


After saving it as ``hello_world.py``, we can see the automatically generated help text::

    $ hello_world.py -h
    usage: hello_world.py [--name NAME] [--help]

    Simple greeting example

    Optional arguments:
      --name NAME, -n NAME        The person to say hello to (default: World)
      --help, -h                  Show this help message and exit (default: False)


We can run it with multiple variations of arguments::

    $ hello_world.py
    Hello World!

    $ hello_world.py -n John
    Hello John!

    $ hello_world.py --name John
    Hello John!


Even without explicitly specifying the long form for the ``name`` `Option`_, it was automatically added based on the
name of the attribute in which that Parameter was stored.

