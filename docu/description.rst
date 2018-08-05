Introduction
============

Lconfig is a simple configuration format and module to parse and generate
line based key value configuration settings.

An Example is better than a lot of words:

.. code-block::

    config.option = value
    # comment line
    default.paths = /home/x
    default.paths = /home/y
    complex_option = simple value

As shown it is line based every line has an "=" asignement with
key on the left and value on the right.
Comment lines start with `#`.

Keys can contain lower alphnumeric characters and `_` and `.`.
Values can contain every unicode character.

Yes this looks like simple property configuraion formats.
And the goal ist to be simple but powerful.


Specification
=============

The format is line based and if read from a file "utf-8" should be used
as default encoding.
Only line comments are allowed and start with `#`, to comment the whole line.
The normal line has a `key`, `=` and a `value`.
For example::

    mykey = some text

Assigns the configuration key `mykey` the value `some text`.

Details:

1. Keys can contain only the following characters:
    ``abcdefghijklmnopqrstuvwxyz`` and ``_.``
2. The ``.`` in a key is used to specify a hirachy or group.
3. Special keys start with a dot ``.`` and are reserved for internal use.
4. Comment lines start with an ``#`` and are not interpreted.
5. Lines before parsing are normalized, whitespaces in front and at the end
   are removed. (stripped)
6. For parsing a line is split into the key and value, they are separated
   by ``=``.
7. The key and value strings are also normalized, whitespaces in front and at
   the end are removed. (stripped)
8. Multiple identical keys are allowed. Every value is recorded
   in a list for the key. The order is preserved. The last asignement is the
   last value in the list.
9. If a key is omited (empty) the asignement is asumeed to be for the last
   know key. (only for reading from a file or stream)

Additional clarification:

- Empty value is allowed and can have a special meaning.

Examples
========

These are file or string examples.

Allowed comments::

    # comment at start of the line
       # also allowed but discouraged

Invalid comments::

    key = value # this is not a comment
    key # invalid comment
    ; also no comment

Keys and values::

    key = value
    option.a = My other VALUE
    option.b = also "some" value
    multi = a
    multi = b
    multi = c
    = d
    another.key=VALUE
    package_path = /home

    .adapter = myadapt


Invalid lines::

    KEY = value
    my/path = /home
    no.asign:ment
    ...

Why?
====

Because configurations are needed at a lot of places and yet more format
could not harm.

No really, I wanted a simple format human readable and easy to parse.
But also with some limitations to avoid common errors often seen in the wild.

So the format allows only lower ASCII characters and numbers.
The ``.`` is used if you want a hirachy and ``_`` is used if a word separator
is needed.
A line contains every information needed. Complex multi line statements are
not allowed. Also only one comment character and one assignement character
is used.
If you want to assign a list of values multiple assignement to the same key
can be used. No need to teach a compley syntax.


The power (dot keys)
====================

Comes from the configuration class provided and the reserved lines starting
with ``.`` for keys. The dot keys.

The dot keys are also valid syntax and specify special keys for internal
use. The main purpose for the is to specify ``.adapt`` and ``.convert`` keys.
Because they are legal config syntax the can also be use in the configuration
file or string to specify handling of values and keys.

As noted the dot in keys specify a hirary this is also valid for dot keys.

Adapter
-------

An adapter is executed when a value is assigned to a key.
``config["key"] = 'my value'``

An adapter returns a list of unicode strings or None.


Converter
---------

A converter is executed when a value for a key is retrieved.
``value = config["key"]``

The input of a converter is a list of unicode strings and the output
is the converted value.


Both adapter and converter operate on the list of unicode strings internally
used to store the configuration. This internal storage format is fixed
and can be easily serialized back into a file or stream with the defined
syntax.


Interpolation
-------------

Only mentioned before but not described in detail.
I self thought long about it, should it be part of the StdConfigParser or not.
For me the conclusion was, it is useful for the end user and can help him/her
a lot. But if not needed in the configuration to have it will not disturb.
The user decides to use it. And because most users are lazy like me and don't
want to change the same value at 1000 places they will use it. It is also
super elegant solution to provide and describe default values.

One possible way is to have an option at the parser for it. But I want to
have one standard way and not two ways. So I decided if you enable it there is
one specified format for it.
We use simply the extended interpolation format of Python configparser module.
Interpolation for the configuration is simple a replace "this by that" at access
time. It is not like a template at parsing time. Really when you access the
key the replacement is done every time again when you access the key. No cache
you are up to date for changes in other places. Don't care about performance
it is not the problem at configuration level. Here we care about most up to date
and good usable defaults. Even if someone changes something at another level.
This is a feature you will later as a user and programmer learn to love and
understand the full power of it.
Lot of other configuration solution do this wrong and prefer performance over
up to date values, which is not what a user want.

Enough text, the format is simple: ``${option}`` to insert the value of the
option when accessing. Or over sections: ``${section:option}``

.. code-block:: ini

    [myapp]
    path = /user
    log_path = ${path}

    [otherapp]
    path = ${myapp:path}/other
    dollarsign = $$



Interpolation can simplify the live for the user by having to specify the
value in one place and use it also in another place.
It can also simplify the application developers live by using it for good
default values.
Because of the ":" as separator between section and key, try to avoid the ":" in
sections. If your section uses ":" in the name only the last ":" is used to
detect the option. Everything before the last ":" is used as section name.
To use the ``$`` sign escape it with another one and use ``$$``.


Interface
---------

Is really a thin wrapper around the Python library ConfigParser with sensible
default values chosen. So you don't have to think about it. You can simple use
this library and it's additional goodies.

The Python standard library configuration parser has a really long list of
options. The StdConfigParser will simplify this to two. I'll describe in detail
the default set for you.

Python ConfigParser init option:

defaults=None

This is a dictionary with your default values. So useful you will get it also
with the same default.

dict_type=collections.OrderedDict

Good default choice, the module uses the default and does not provide an option
here.

allow_no_value=False

Good default. Use the same and will not provide this option. It brings up
configuration errors earlier. If the user has forget to specify a value this will
be an error.

delimiters=('=', )

The StdConfigParser allows only "=" as key value delimiter. No changes possible.

comment_prefixes=('#', )

The StdConfigParser allows only "#" as a comment prefix. One way is enough to
comment.

inline_comment_prefixes=None

The default is used and not provided as option to the outside. It is also good
to have no inline comment prefix. As the documentation states, it can prevent
some characters in values or have wrong values.

strict=True

Default is used not provided to the outside. Don't allow duplicate sections or
options. The user will get errors earlier.


empty_lines_in_values=True

We allow this and it is good for multi line values. Cannot be changed.


default_section=configparser.DEFAULTSECT

We use the default and provide this option not to the outside.


interpolation=ExtendedInterpolation()

We use the ExtendedInterpolation class. But this is not optional.


converters=None

Instead of the default "{}" we use None. I don't like mutable default values.
But internally an empty dictionary is used as default. This option is the second
one available. Can be useful for your own converter functions. But keep in mind
don't overact it. The StdConfigParser provides two additional one for you.


Goodies
-------

Sometimes you need a little bit more than a simple string as a value.
The ConfigParser provides converter functions for you for the most basic
types like: int, bool, float usable by parser.getint(), parser.getfloat()
and parser.getboolean() function.
If you use these functions the value will be converted for you as specified.
And yes by using converters you can really do a lot. Still keeping the
configuration format simple but providing real benefit for your application.

Here comes the difference of the StdConfigParser to other configuration formats.
It invents not a completely new configuration syntax nor a complete new parser.
It uses the existing stuff and specifies and extends it where useful.

Often there is the need to have a more complex configuration structure.
Multiple values nested structure and more. I know the real need but as most
other people did the wrong and mad all this part of my configuration syntax.
Complicating everything.
The StdConfigParser does this not. The user of a configuration file should not
learn a new syntax. Everything is section, key (option) value format. The value
is documented by the application how the string is interpreted.

Listing of values (``getlisting``)
----------------------------------

You have the need to list some short values. The normal way if you write text
is to do this by simply separating them by ``,``. This is also a good solution
in a configuration value. Use this if you list short values and the length
of the list is also short. If you want list longer values use the feature
described in multiple values.

Example:

.. code-block:: ini

    [section]
    listing = env1,env2,env3


Each value will be striped and empty values are ignored by ``getlisting``.
Use it if you want enumerate short string values.
They can also be split over multiple lines. But this is not a feature only to
be fault tolerant. If you have more or longer values use the ``getlines``
feature described in the next section.


Multiple values (``getlines``)
------------------------------

For most configurations there are extended use cases. One is to specify a
list of longer values. The simplest way for an user is to specify this line by line,
every line is a value. For the application this is the method "getlines".
A simple helping converter allowing a easy multi line value syntax.

Example:

.. code-block:: ini

    [section]
    multiline = value 1
                value 2
                value 3
                # comment for four
                value 4

                value 5

    simple_indent_multi_is_enough =
        line 1
        line 2
        line 3


As you can see, simple valid multi line syntax. Easy for the user to see this
is a list of values.
The "getlines" function on the parser does all other for you. It returns a list
with the string values for you. Every line is one value in the list. Comments
and empty lines are removed. So you get a clean list and the user has the
possibility to comment it values and have empty lines to separate some values.

Even for your application you can still do some other list handling like
the values are separated with "," and in one line and have a custom parser for
it. I recommend simple use the getlines function and multiline value feature
for this use case.




Style guide
===========

Yes it makes sense to have also a style guide for configuration. The format
allows some stuff and not everything is an error but considered bad style.


Sections
--------

White space before and after the section name are allowed but everything between
the "[" and "]" is the section name. So don't use spaces before or after the
section name. Also the name is case sensitive, to keep it simple use only lower
case letters for the name.

Sections can be indented but avoid this. Even if you do something like
partitioning of the section name. Keep it flat.

Example:

.. code-block:: INI

    # good style
    [mymodulename]

    # bad style
    [  mymodule  ]

        [mymodule]


Keys and values
---------------

Use a space before the "=" and after it. You cannot prevent your users from
doing different things but for best practice in documentation and for your
default configuration use this style.

Example:

.. code-block:: INI

    # good style
    [mymodule]
    key = value

    # bad style
    keybad1=value
      keybad2 = value
      keybad3=value


Indention
---------

Is useful for values to have them over multiple lines. Try to use it only in
this case. Try to use the same indention level. Preferred are four spaces.
Same as the Python standard. Don't indent sections. Don't use multiple levels
of indention. Keep it simple for your user. Everytime something is indented it
should be a string for a multiline value, nothing more.
Only if you use complex value format like JSON, it makes sens to use additional
indention. But in this case it should be only for visibility.

Example:

.. code-block:: INI

    # good style
    [mymodule]
    key = value over
        multiple
        lines

    another =
        multi
        line
        value

    # bad style
    keybad1 = value over
      multiple
        lines

      keybad2 = value
        multi
        line

    keybad3 =
        value
           more value
              more value


API
===

It has the same api as the :class:`configparser.ConfigParser` from Python 3.5.
But if a text file is read, the default encoding is ``UTF-8``.
The constructor is simplified to have only ``defaults``, ``converters`` and
the ``interpolate`` flag.
Two converters are added by default:

1. listing (getlisting)
2. lines (getlines)


.. function:: getlisting(section, option, raw=False, vars=None [, fallback])

    Handles listing of values. Each value is separated by ``,``. Returns
    a list with none empty values. White space's are stripped. The values are
    split by ``,``.

    Example::

        key = py33,py34, py35

        -> ["py33", "py34", "py35"]


.. function:: getlines(section, option, raw=False, vars=None [, fallback])

    Converts multi line values into a list of values. Each line is fetched
    without the indent. Comments and empty lines are removed.
    But the line is returned as is and not striped. It can contain spaces
    at the end or in front. If you need a striped result ``getlisting`` can
    be used.

    Example::

        key = value 1
              value 2
              # comment
              value 3

        -> ["value 1", "value 2", "value 3"]


All converters are also available at the section proxy level without the
``section`` parameter then.


Examples
========

.. note:: The example section is still work in progress. Not all are ready
          and the code is not tested yet and can contain errors.


Examples describe a special use case and the solution how to handle
this with the StdConfigParser.

Simple usage
------------

You need a configuration for a small module only with some configuration
keys. No need for a nested configuration.

In this case you will have one line overhead, the section. Use the same
name as your module or package as section name. This enables later use
of one configuration file for different packages. Even if you don't need it
know, it is for interoperability.

Example:

Your module or package name is 'mymodule'

.. code-block:: INI

    [mymodule]
    data_dir = /data
    temp_dir = /temp

In your program code create the config parser instance retrieve the section
and only use your section.

.. code-block:: Python

    from stdconfigparser import StdConfigParser

    def get_config(path):
        parser = StdConfigParser()
        parser.read(path)
        config = parser["mymodule"]
        return config

    def main():
        config = get_config("~/mymodule.cfg")
        data_dir = config.get("data_dir")
        temp_dir = config.get("temp_dir")


Default values
--------------

The configuration file is only for you and there are global default values
needed. So a user specifies a option only if he/she does not want the default
value.

Example:

Your module or package name is 'mymodule'

.. code-block:: INI

    [mymodule]
    data_dir = /data

In your program code create the config parser instance retrieve the section
and only use your section.

.. code-block:: Python

    from stdconfigparser import StdConfigParser

    def get_config(path):
        parser = StdConfigParser(defaults={"data_dir": "./data",
                                           "temp_dir": "./tmp"})
        parser.read(path)
        config = parser["mymodule"]
        return config

    def main():
        config = get_config("~/mymodule.cfg")
        data_dir = config.get("data_dir")
        temp_dir = config.get("temp_dir")


In this case the for the 'temp_dir' option your provided default value is used.


List of values
--------------

Most of your values are simple but some need to list something. Most of the
time it is a list of allowed stuff or short labels.
In this case you can use the ``getlisting`` converter provided out of the box.


Example:

.. code-block:: INI

    [mymodule]
    build_platforms = Linux, Windows, OSX
    build_labels = html, pdf, exe, shared
    multiline_listing = a, stuff,
        b, more stuff,
        c, last element


In your program code use the ``getlisting`` method of configparser. It returns
a list with the values for you.


.. code-block:: Python

    from stdconfigparser import StdConfigParser

    def get_config(path):
        parser = StdConfigParser()
        parser.read(path)
        config = parser["mymodule"]
        return config

    def main():
        config = get_config("~/mymodule.cfg")
        platforms = config.getlisting("build_platform")
        labels = config.getlisting("build_labels")


Values are separated by ',' in this case. They can be in one line or specified
over multiple line.


Multi line values
-----------------

You need to specify a list of values each in one line. The values can be
really long and you want not allow them to be at the same line because of
readability.
In this case you can use the ``getlines`` converter provided out of the box.


Example:

.. code-block:: INI

    [mymodule]
    requirements =
        StdConfigparser >= 0.6
        Python >= 2.7
        FancyXMLHTMLParser
        Sphinx


In your program code use the ``getlines`` method of configparser. It returns
a list with the values for you.


.. code-block:: Python

    from stdconfigparser import StdConfigParser

    def get_config(path):
        parser = StdConfigParser()
        parser.read(path)
        config = parser["mymodule"]
        return config

    def main():
        config = get_config("~/mymodule.cfg")
        requirements = config.getlines("requirements")

With this you get a list of your requirements for every line one entry.
No need to specify a separator.


Multiple sections
-----------------

You need a little bit more structure in the configuration and you want
to configure reoccurring stuff like a list of environments with same
options in them.
You have your main configuration in a section and for every environment also
a section. The environment section is prefixed with the main section name.
Your users are free to add more environment sections if needed.
In the main section there is a list with the active environments.

.. code-block:: INI

    [mymodule]
    environments = py33,py35,py27

    [mymodule py33]
    path = py33

    [mymodule py34]
    path = py34

    [mymodule py35]
    path = py35

    [mymodule py27]
    path = py27


In your program code get the environment list and use it directly or get
the sections and check if they are active. Most is up to the application to
handle this only the getlines() helper method of StdConfigParser is used.

.. code-block:: Python

    from stdconfigparser import StdConfigParser

    def get_config(path):
        config = StdConfigParser()
        config.read(path)
        return config

    def main():
        config = get_config("./mymodule.cfg")
        envprefix = "mymodule "

        environments = config.getlisting("mymodule", "environments")
        for environment in environments:
            path = config.get(envprefix + environment, "path", fallback=".")
            # you get only the specified without py34 path
            # it is also got to use fallback here if a environment is listed
            # but no configuration value is provided

If you have more than one listing for your multiple sections it can be better
to use a namespace then. Something like ``[mymodule.env.py33]`` for a section.
And access the section with ``envprefix = "mymodule.env."``. Basic technique
described in next example.


Multiple sections namespace package
-----------------------------------

You have a main applications which uses a namespace package to handle
your plugins.
In this case it is good to have a section for every module of your namespace
package. Can still by useful to have one main configuration key using the same
name as your namespace. Because it is natural for packages to use the "."
separator it is also use for the section. So the name of the section already
matches the full module name.

.. code-block:: INI

    [namespace]
    base_path = .

    [namespace.mod1]
    max_number = 100

    [namespace.mod2]
    fast_processing = true

    [namespace.mod3]
    deep = false


In the program code every module can access his own configuration section.
The main application can also list all modules of the namespace.

.. code-block:: Python

    from stdconfigparser import StdConfigParser

    def get_config(path):
        config = StdConfigParser()
        config.read(path)
        return config

    def main():
        config = get_config("./namespace.cfg")
        namespace = "namespace"
        namespace_prefix = namespace + "."

        submodules = [v[len(namespace_prefix) for v in config.sections()
                      if v.startswith(namespace_prefix)]


Multiple sections no sharing with others
----------------------------------------

Your application is the only one using the configuration file. No sharing
with other applications is needed. But you need a little bit structure
to make the life for your users easier.
In this case use the sections for a simple structure and name them as needed.


.. code-block:: INI

    [hosts]
    aname = value1
    bname = value2

    [targets]
    xname = valx
    yname = valy

    [logging]
    level = debug
    file = a.log
    system = false


The usage of this configuration is simple, access with the sections the
special stuff. Parse the configuration file normally and use the full power
of the configparser.


Interpolation and defaults
--------------------------

You want to have default values for most of your configuration options.
But you share the configuration with other applications and the defaults are
only in your section.
A good solution for this is to use interpolation with your defaults in an
dictionary with your section. Read your defaults before you read the
configuration from a file or other source.

Use the global defaults to only specify common stuff for all sections.
Something like the configuration directory. Your default values can than
use this in combination with interpolation to set default values in a section.

.. code-block:: Python

    my_defaults = {"mymodule": {
      "project_dir": "${config_dir}/..",
      "log_dir": "${project_dir}/log",
      "data_dir": "${project_dir}/data",
      "temp_dir": "${project_dir}/tmp",
    }}


.. code-block:: INI

    [mymodule]
    project_dir = /usr/home/special/project


.. code-block:: Python

    import os
    from stdconfigparser import StdConfigParser

    def get_config(path):
        config_dir = os.path.abspath(os.path.dirname(path))
        parser = StdConfigParser(defaults={"config_dir": config_dir})
        parser.read_dict(my_defaults)
        parser.read(path)
        config = parser["mymodule"]
        return config

    def main():
        config = get_config("~/mymodule.cfg")
        data_dir = config.get("data_dir")

Here you set only one global default, your 'config_dir'. This is then
used in your default configuration for your section but only by interpolate
values. You read in your default configuration dictionary before the
configuration form the file. With this order they act as default values.
The user can overwrite what is needed in the configuration file. If nothing is
overwritten your defaults are used.


Config file with interpolation
------------------------------

Your use case is to have a configuration file in a specific configuration
directory. The directory path should also be usable in the configuration
as interpolation value.

Use the defaults parameter to set the configuration directory.

.. code-block:: INI

    [mymodule]
    project_dir = ${config_dir}/..
    log_dir = ${project_dir}/log
    temp_dir = ${project_dir}/tmp


.. code-block:: Python

    import os
    from stdconfigparser import StdConfigParser

    def get_config(path):
        config_dir = os.path.abspath(os.path.dirname(path))
        parser = StdConfigParser(defaults={"config_dir": config_dir})
        parser.read(path)
        config = parser["mymodule"]
        return config

    def main():
        config = get_config("~/mymodule.cfg")
        project_dir = config.get("project_dir")


Environment information
-----------------------

The os environment information is needed in the configuration as as
interpolation value.
The solution is simple, add a section with this information before you read
your configuration. Don't write it to the default section, make it explicit
into a new documented section. In the configuration this section can be used
for substitutions. Document also the environment information will not be updated
it is only read at startup.

.. code-block:: INI

    [mymodule]
    project_dir = ${os.environ:home}

In this example the environment section is simply named by the Python module path.
``os.environ``. But if you prefer a shorter solution you can use the name ``env``
which is also common to name the environment.
The environment information is also read before the configuration, this allows
overwriting in the configuration file. Can be used as a feature for testing.

.. code-block:: Python

    import os
    from stdconfigparser import StdConfigParser

    def get_config(path):
        parser = StdConfigParser(interpolate=True)
        parser.read_dict({"os.environ": os.environ}, "environment")
        parser.read(path)
        config = parser["mymodule"]
        return config

    def main():
        config = get_config("~/mymodule.cfg")
        project_dir = config.get("project_dir")

For environment information keep in mind it can bring in a can of worms for
your application. Better is to only provide a defined set of variables
as defaults for the configuration.


Additional converter, getjson
-----------------------------

Sometimes, you have the need for more complex configuration
structure. If you cannot avoid it and you really need something like a deeper
structure or you have demand of types in your value lists I have also a solution
for it. The solution is JSON. Why? What?
Yes in this complex case I don't reinvent the wheel. Most users for a
Python application are already familiar to the Python syntax and JSON is nearly
similar. It is documented and easy to read/write.
But you may ask, I want to comment complex stuff. The answer is, yes you can.
Comments are handled by the ConfigParser in a normal way. Only line comments are
allowed. Also empty lines. But value indent must also be kept for JSON values.
Even if you use JSON values keep in mind the value is handled as multi line
string by the parser before you get it.


Example:

.. code-block:: INI

    [mymodule]
    json_value = {"key": "value", "int_value": 100}
    json_list = [1, 2, 3, 4, "five"]
    complex = {"name": "test_environ",
               "paths":
                  ["/home/username",
                   "/usr/local/bin"]
              }


.. code-block:: Python

    import json
    from stdconfigparser import StdConfigParser

    def get_config(path):
        config = StdConfigParser(converters={"json": json.loads})
        config.read(path)
        return config

    def main():
        config = get_config("~/mymodule.cfg")
        value = config.getjson("mymodule", "json_value")
        list_value = config.getjson("mymodule", "json_list")
        complex_value = config.getjson("mymodule", "complex")


As you can see, these are still valid string values but if you use
the "getjson" method of the parser, the value will be parsed for you
and you get back the Python values. Comments are allowed, empty lines also
as known by multi line configuration values. The user has the possibility
to write it in a readable way. The application let Python parse the syntax in
a safe way. This is really powerful. You can do nearly all complex configuration
needs with it. Even to complex for the user. Keep this in mind.
If you know this, use it only for the configuration keys where it is really
needed. You have the power but your users must be able to handle it.


Additional converter, getliteral
--------------------------------

You want to provide really powerful configuration values to your users.
Only Python 3 is used and you know your users are experienced Python developers
and can handle this complexity. Really only in this case!
Then you can add a converter based on Pythons ``ast.literal_eval`` function.
In other cases try first to use the JSON converter for complex stuff.

Why only for Python 3? Because of Unicode and the way it is handled in Python 2.
You don't want to specify every string in your configuration with
``u"my string"`` to do it right.


Example:


.. code-block:: ini

    [section]
    key = ['some value in a list']

    object = {"data": "in a dict", "x": 10, 1:'1'}

    now_it_gets_complex = {
        "key": "value",
        # with comment
        "set": {1, 3, 4}, # in line comment handled in value
        "tuple": (1,2,3),
        "None": None,
        }


.. code-block:: Python

    import ast
    from stdconfigparser import StdConfigParser

    def get_config(path):
        config = StdConfigParser(converters={"literal": ast.literal_eval})
        config.read(path)
        return config

    def main():
        config = get_config("~/mymodule.cfg")
        value = config.getliteral("section", "object")
        list_value = config.getliteral("section", "key")
        complex_value = config.getjson("section", "now_it_gets_complex")


With this additional converter you have can have really complex values in
your configuration. Even to complex. So be careful and extend only if you
need it and your users are able to handle it.


Config file includes
--------------------

In a big application sometimes there is the need to have more than one
configuration file. But one main file should be used to specify the other
include files.

In this case best is to donate a special key named ``include`` with multi line
values to name the additional files. Try to avoid recursive includes and other
more complex stuff here. A feature you thought to be useful can bring you
near to the hell.

Best here is to support absolute paths and relative paths. Where a relative
path starts with a ``.`` (dot) and is relative to the specified configuration
file.

.. code-block:: INI

    [mymodule]
    include = ./names.cfg
              ./connections.cfg
              /etc/mymodule.cfg

    project_name = lotincludes

To solve this we read the main configuration file to get the included ones.
Build the paths for the files to handle the relative ones.
Read them and overwrite the result with the main configuration. Because this
is what most users expect.


.. code-block:: Python

    import os
    from stdconfigparser import StdConfigParser

    def get_config(path):
        config_dir = os.path.abspath(os.path.dirname(path))
        main_config = StdConfigParser()
        main_config.read(path)
        config_include = main_config.getlines("mymodule", "include", fallback=[])
        includes = []
        for include in includes:
            if include.startswith("."):
                include = os.path.abspath(os.path.join(config_dir, include))
            includes.append(include)
        includes.append(path) # read origin as last config
        config = StdConfigParser()
        config.read(includes)
        return config

    def main():
        config = get_config("~/mymodule.cfg")
        project_dir = config.get("myproject", "project_dir")


In this example the specified configuration files are read in order the last
can overwrite stuff from others, your main config file options win.
If a specified config include is not there it is silently ignored.
Optionally you can get the read files list and log it or other stuff.
The main config file is read twice, first to get the includes and also
as last file to overwrite other settings. You can optimize this to only read
the main file once but keep in mind not to use read_dict method of config for
this, because it uses items on the config and this evaluates all interpolations.
This is not what you want. But a config file normally is not of gigabytes in
size. Hence reading twice doesnÄt hurt.
