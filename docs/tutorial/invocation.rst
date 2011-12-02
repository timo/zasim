.. _tutorial_invocation:

Invoking zasim from the commandline
===================================

The easiest, simplest way to start with zasim is to try out its
commandline-based ascii-art drawing module, `zasim.cagen.main`. It can either
be called directly like this

.. command-output:: python -m zasim.cagen.main --help
  :shell:
  :ellipsis: 3

or using the script `zasim_cli`, that setuptools installs in your system when
installing the zasim package:

.. command-output:: zasim_cli --help
  :shell:

Let's start with a simple example, displaying a run of a `elementary
cellular automaton`_ - I personally like rule number 126, which generates
triangles.

.. command-output:: zasim_cli --rule 126 --pure
    :ellipsis: 15

Don't concern yourself with the *--pure* option yet. It will be explained later.

The option *--print-rule* will cause the program to print out the rule
table that it uses to do each step as well as the rule number in decimal
and hexadecimal:

.. command-output:: zasim_cli --rule 126 --pure --print-rule
    :ellipsis: 10

..
    this is a really cool CA with base 3.
    0x58783d3e65d

If you want the image to fill the width of your console, you can supply
$COLUMNS for the *--width* parameter and with *--steps* you can limit how
many lines it will display before it stops calculating.

.. _elementary cellular automaton: http://en.wikipedia.org/wiki/Elementary_cellular_automaton


beta and nondet
---------------

There are two more interesting switches for this module: *--beta* and *--nondet*.

Both of them cause the calculation to behave nondeterministically. The
simpler one to explain is *--nondet*:

When supplying a percentage (that is, a value between 2 and 100 or a floating
point value between 0.0 and 1.0) to *--nondet*, each cell will only executed
with a probability given as the percentage. If it doesn't execute, its new value
is simply the old value.

Take, for instance, the rule 0, which sets every cell to 0 in every step,
no matter what the previous value was.

.. command-output:: zasim_cli --rule 0 --print-rule --pure --nondet 5
    :ellipsis: 30

With a nondet value of 5, only 5% of all cells get set to 0 in each step
and the configuration turns all spaces pretty soon.

*--beta* is a little bit more complicated, but described in detail in the
section of `zasim.cagen.beta_async`.

Here is one example of a beta-asynchronous version of rule 146, which would
normally make lots and lots of triangles. With 70% beta-async, it breaks
the triangle structures quite noticably.

.. command-output:: zasim_cli --rule 146 --width 90 --print-rule --pure --beta 0.7
    :ellipsis: 40

 
base
----

The traditional elementary cellular automaton is based on cells that have
either the value 0 or 1. The concept can easily be extended to cells with
an arbitrary number of different values. By supplying the *--base*, you
can choose any number, but higher values cause a very steep incline of
rule numbers. Also, at one point the palette of ascii characters that are
configured for zasim will run out.

The default base is, of course, 2. Supplying a base of 1 is nonsensical,
because every cell could only have the value 0.


The mysterious pure flag
------------------------

zasim can not only run the computations using regular - but usually slow
- python code. It can also execute the step functions in generated C code
instead, which gives a pretty noticable performance improvement.

For this to work, however, you need to have `SciPy` installed on your system.

