#!/usr/bin/env python

from cli_command_parser import Command, main, ParamGroup, before_main, after_main


class GroupedFlags(Command):
    with ParamGroup(mutually_exclusive=True):

        @before_main('-a', order=1)
        def action_a(self):
            print('a')

        @before_main('-b', order=2)
        def action_b(self):
            print('b')

        with ParamGroup(mutually_dependent=True):

            @before_main('-c', order=3)
            def action_c(self):
                print('c')

            @before_main('-d', order=4)
            def action_d(self):
                print('d')

    with ParamGroup(mutually_dependent=True):

        @after_main('-w', order=1)
        def action_w(self):
            print('w')

        @after_main('-x', order=2)
        def action_x(self):
            print('x')

        with ParamGroup(mutually_exclusive=True):

            @after_main('-y', order=3)
            def action_y(self):
                print('y')

            @after_main('-z', order=4)
            def action_z(self):
                print('z')

    def main(self):
        print('main')


if __name__ == '__main__':
    main()
