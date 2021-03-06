Input Types
***********

Parameters that accept a :ref:`parameters:parameters:type` parameter can accept any callable to transform parsed
argument values, but some custom types are defined here to facilitate common use cases.


Paths & Files
=============

Path
----

To automatically handle common normalization steps / checks that are done for paths, the :class:`.Path` class is
available.

.. _path_init_params:

**Path initialization parameters:**

:exists: If set, then the provided path must already exist if True, or must not already exist if False.  By default,
  existence is not checked.
:expand: Whether tilde (``~``) should be expanded.  Defaults to True.
:resolve: Whether the path should be fully resolved to its absolute path, with symlinks resolved, or not.  Defaults to
  False.
:type: To restrict the acceptable types of files/directories that are accepted, specify the :class:`.StatMode` that
  matches the desired type.  By default, any type is accepted.  To accept specifically only regular files or
  directories, for example, use ``type=StatMode.DIR | StatMode.FILE``.
:readable: If True, the path must be readable.
:writable: If True, the path must be writable.
:allow_dash: Allow a dash (``-``) to be provided to indicate stdin/stdout (default: False).


Given the following (truncated)
`example <https://github.com/dskrypa/cli_command_parser/blob/main/examples/custom_inputs.py>`__::

    from cli_command_parser import Command, Option, main, inputs as i

    class InputsExample(Command):
        path = Option('-p', type=i.Path(exists=True, type='file'), help='The path to a file')

        def main(self):
            if self.path:
                self.print(f'You provided path={self.path}')


The resulting output::

    $ custom_inputs.py -p examples
    argument --path / -p: bad value='examples' for type=<Path(exists=True, type=<StatMode:FILE>)>: expected a regular file

    $ custom_inputs.py -p examples/custom_inputs.py
    You provided path=examples/custom_inputs.py

    $ custom_inputs.py -p examples/custom_inputs.p
    argument --path / -p: bad value='examples/custom_inputs.p' for type=<Path(exists=True, type=<StatMode:FILE>)>: it does not exist


File
----

The :class:`.File` custom input extends :ref:`inputs:Path`, so it can accept all of the same options, but it provides
functionality for directly reading or writing to the provided path.

.. _file_init_params:

**Additional File initialization parameters:**

:mode: The mode in which the file should be opened.  Defaults to ``r`` for reading text.  For more info,
  see :func:`python:open`.
:encoding: The encoding to use when reading the file in text mode.  Ignored if the parsed path is ``-``.
:errors: Error handling when reading the file in text mode.  Ignored if the parsed path is ``-``.
:lazy: If True, a :class:`.FileWrapper` will be stored in the Parameter using this File, otherwise the file will be
  read immediately upon parsing of the path argument.


Using another snippet from the above
`example <https://github.com/dskrypa/cli_command_parser/blob/main/examples/custom_inputs.py>`__::

    class InputsExample(Command):
        in_file = Option('-f', type=i.File(allow_dash=True, lazy=False), help='The path to a file to read')
        out_file: i.FileWrapper = Option('-o', type=i.File(allow_dash=True, mode='w'), help='The path to a file to write')

        def main(self):
            if self.in_file:
                self.print(f'Content from the provided file: {self.in_file!r}')

        def print(self, content):
            if self.out_file:
                self.out_file.write(content + '\n')
            else:
                print(content)


We can see the results::

    $ echo 'stdin example' | custom_inputs.py -f-
    Content from the provided file: 'stdin example\n'

    $ echo 'stdin example' | examples/custom_inputs.py -f- -o example_out.txt

    $ cat example_out.txt
    Content from the provided file: 'stdin example\n'


By setting ``lazy=False``, the ``in_file`` Option in the above example eagerly loaded the content, so the entire file
contents were stored in the Parameter.  The default is for only the path to be stored, and a :class:`.FileWrapper` that
has :meth:`.FileWrapper.read` and :meth:`.FileWrapper.write` methods is returned.  The file will only be opened for
reading/writing when those methods are called, as can be seen in the example when ``self.out_file.write(...)`` is
called.


Serialized Files
----------------

In addition to plain text or binary files, custom input handlers also exist for :class:`.Json` and :class:`.Pickle`,
and a generic handler (:class:`.Serialized`) exists for any other serialization format.  They all extend
:ref:`inputs:File`, so the same options are accepted.

.. _serialized_init_params:

**Additional Serialized initialization parameters:**

:converter: The function to call to serialize or deserialize the content in the specified file
:pass_file: True to call the given function with the file, False to handle (de)serialization and read/write as
  separate steps.  If True, when reading, the converter will be called with the file as the only argument; when writing,
  the converter will be called as ``converter(data, f)``.  If False, when reading, the converter will be called with
  the content from the file; when writing, the converter will be called before writing the data to the file.


The JSON and Pickle handlers do not accept the above 2 parameters.  The converter is automatically picked to be
``dump`` or ``load`` based on whether the provided ``mode`` is for reading or writing, and the ``pass_file``
option will be overridden if provided.


Adding another snippet to the above
`example <https://github.com/dskrypa/cli_command_parser/blob/main/examples/custom_inputs.py>`__::

    class InputsExample(Command):
        json: i.FileWrapper = Option('-j', type=i.Json(allow_dash=True), help='The path to a file containing json')

        def main(self):
            if self.json:
                data = self.json.read()
                self.print(f'You provided a {type(data).__name__}')
                iter_data = data.items() if isinstance(data, dict) else data if isinstance(data, list) else [data]
                for n, line in enumerate(iter_data):
                    self.print(f'[{n}] {line}')


We can see that the JSON content from stdin was automatically deserialized when ``self.json.read()`` was called::

    $ echo '{"a": 1, "b": 2}' | examples/custom_inputs.py -j -
    You provided a dict
    [0] ('a', 1)
    [1] ('b', 2)


When using the generic :class:`.Serialized` directly, the specific (de)serialization function needs to be provided::

    Serialized(pickle.loads, mode='rb', lazy=False)
    Serialized(pickle.load, pass_file=True, mode='rb', lazy=False)

    Serialized(json.loads, lazy=False)
    Serialized(json.load, pass_file=True, lazy=False)

    Serialized(json.dumps, mode='w')
    Serialized(json.dump, pass_file=True, mode='w')



Numeric Ranges
==============

Range
-----

To restrict the allowed values to only integers in a :class:`python:range`, the :class:`.Range` input type is available.

For convenience, Parameters can be initialized with a normal :class:`python:range` object as ``type=range(...)``,
and it will automatically be wrapped in a :class:`.Range` input handler.  To use the ``snap`` feature, :class:`.Range`
must be used directly.

.. _range_init_params:

**Range initialization parameters:**

:range: A :class:`python:range` object
:snap: If True and a provided value is outside the allowed range, snap to the nearest bound.  The min or max
  of the provided range (not necessarily the start/stop values) will be used, depending on which one the provided
  value exceeded.


NumRange
--------

The :class:`.NumRange` input type can be used to restrict values to either integers or floats between a min and max,
or only bound on one side.  At least one of min or max is required, and min must be less than max.

By default, the min and max behave like the builtin :class:`python:range` - the min is inclusive, and the max is
exclusive.

.. _numrange_init_params:

**NumRange initialization parameters:**

:type: The type for values, or any callable that returns an int/float.  Defaults to float if one or both of min or max
  is a float, otherwise int.
:snap: If True and a provided value is outside the allowed range, snap to the nearest bound.  Respects inclusivity
  / exclusivity of the bound.  Not supported for floats since there is not an obviously correct behavior for handling
  them in this context.
:min: The minimum allowed value, or None to have no lower bound.
:max: The maximum allowed value, or None to have no upper bound.
:include_min: Whether the minimum is inclusive (default: True).
:include_max: Whether the maximum is inclusive (default: False).



Choice Inputs
=============

Choice inputs provide a way to validate / normalize input against a pre-defined set of values.


Choices
-------

Validates that values are members of the collection of allowed values.  Choices may be provided to Parameters as
either ``choices=...`` or as ``type=Choices(...)``.  If they are provided as ``choices=...``, then a :class:`.Choices`
input type will automatically be created to handle validating those choices.  Any ``type=...`` argument to the
Parameter will be passed through when initializing the :class:`.Choices` object.  To adjust case-sensitivity,
:class:`.Choices` must be initialized directly.

If ``choices`` is a dict or other type of mapping, then only the keys will be used.  See :ref:`inputs:ChoiceMap` for
another option for handling dicts.

.. _choices_init_params:

**Choices initialization parameters:**

:choices: A collection of choices allowed for a given Parameter.
:type: Called before evaluating whether a value matches one of the allowed choices, if provided.  Must accept
  a single string argument.
:case_sensitive: Whether choices should be case-sensitive.  Defaults to True.  If the choices values are not
  all strings, then this cannot be set to False.


ChoiceMap
---------

Similar to :ref:`inputs:Choices`, but requires a mapping for allowed values.

.. _choicemap_init_params:

**ChoiceMap initialization parameters:**

:choices: Mapping (dict) where for a given key=value pair, the key is the value that is expected to be
  provided as an argument, and the value is what should be stored in the Parameter for that argument.
:type: Called before evaluating whether a value matches one of the allowed choices, if provided.  Must accept
  a single string argument.
:case_sensitive: Whether choices should be case-sensitive.  Defaults to True.  If the choices keys are not
  all strings, then this cannot be set to False.


EnumChoices
-----------

Similar to :ref:`inputs:ChoiceMap`, but the :class:`.EnumChoices` input uses an Enum to validate / normalize input
instead of the keys in a dict.  Facilitates the use of Enums as an input type without the need to provide a redundant
``choices`` argument for accepted values or implement ``_missing_`` to be more permissive.

If incorrect input is received, the error message presented to the user will list the names of the members of the
provided Enum, as they would if they were provided as ``choices``.

For convenience, Parameters can be initialized with a normal Enum subclass as ``type=MyEnum``, and it will
automatically be wrapped in a :class:`.EnumChoices` input handler.  If an Enum is provided as the type, and
``choices=...`` is also specified, then the Enum will not be wrapped.  To enable case-sensitive matching,
:class:`.EnumChoices` must be used directly.

.. _enumchoices_init_params:

**EnumChoices initialization parameters:**

:enum: A subclass of :class:`python:enum.Enum`.
:case_sensitive: Whether choices should be case-sensitive.  Defaults to False.
