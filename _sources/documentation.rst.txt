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
  :alt: Group tree example output showing the difference between visual indicators for each type of group

If the output appears garbled compared to the above example, it is likely due to lack of correct UTF-8 support in the
terminal.  When using PuTTY, make sure the ``Remote character set`` (in the ``Window`` > ``Translation`` config
category) is configured to use ``UTF-8``:

.. image:: images/putty_utf-8.png
  :alt: Screenshot of the "Remote character set" setting location in a PuTTY configuration window


reStructuredText
================

It is possible to easily generate `RST / reStructuredText <https://docutils.sourceforge.io/rst.html>`__ for a given
Command or file containing one or more Commands.  The generated RST content can then be used to generate documentation
in HTML and many other formats by using `Sphinx <https://www.sphinx-doc.org/en/master/>`__ or any other tool that
supports RST.

Some of the :ref:`configuration:Usage & Help Text Options` also apply to RST generation.


Generating RST Documentation
----------------------------

All you need to generate documentation for a given script that contains one or more Commands is something like
the following::

    from cli_command_parser.documentation import render_script_rst

    def save_command_rst(script_path, rst_path):
        rst = render_script_rst(script_path)
        with open(rst_path, 'w') as f:
            f.write(rst)


If you want more fine-grained control over RST generation than :func:`.render_script_rst` provides, you can use
:func:`.render_command_rst` for a single command.  In the same module, a helper for
:func:`loading all Commands<.load_commands>` from a given file is also provided.

The `build_docs.py <https://github.com/dskrypa/cli_command_parser/blob/main/bin/build_docs.py>`__ script used to
generate this documentation uses :func:`.render_script_rst` to generate the :doc:`examples` documentation based on the
`examples <https://github.com/dskrypa/cli_command_parser/tree/main/examples>`__ in this project.

Building HTML documentation from the output is possible with ``sphinx-build`` and other tools, but that is out of scope
for this guide.
