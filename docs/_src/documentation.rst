Documentation
*************

Help Text
=========

The ``--help`` / ``-h`` option is automatically added to Commands by default.  When specified, it takes precedence over
any other parameters.  The usage / help text that it prints is automatically generated based on the Command in use,
the file it is in, the Parameters in that Command, and any subcommands that are present.

The content of the help text can be configured when :ref:`initializing the Command <commands:Initializing Commands>`.
It is also possible to :ref:`disable <configuration:Usage & Help Text Options>` the ``--help`` parameter by specifying
``add_help=False``, if desired.  If ``add_help`` is disabled, it is possible to define a different
:ref:`parameters:ActionFlag` to replace it, using a combination of
:paramref:`always_available=True<.ActionFlag.always_available>`, ``before_main=True``, and ``order=-1`` (or another
number that is lower than any other ActionFlag in the Command).


Group Formatting
----------------

To add a visual indicator for groups of parameters, specify ``show_group_tree=True``.  Example::

    class Foo(Command, show_group_tree=True):
        ...

Using the `grouped_action_flags example <https://github.com/dskrypa/cli_command_parser/blob/main/examples/grouped_action_flags.py>`__,
we can see an example of the resulting help text:

.. image:: images/show_group_tree_example.png


reStructuredText
================

It is possible to easily generate `RST / reStructuredText <https://docutils.sourceforge.io/rst.html>`__ for a given
Command or file containing one or more Commands.  The generated RST content can then be used to generate documentation
in HTML and many other formats by using `Sphinx <https://www.sphinx-doc.org/en/master/>`__ or any other tool that
supports RST.

All of the `examples <https://github.com/dskrypa/cli_command_parser/tree/main/examples>`__ in this project have been
:doc:`documented <examples>` using this process so you can see the generated results.  It's even possible to integrate
with your tooling to add additional content or customize it before saving / passing the RST content to Sphinx.





