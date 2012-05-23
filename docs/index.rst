Welcome to zasim
================

zasim is a python package for simulating and developing cellular automatons.

Its current features are:

  - Reduction of boilerplate code and modularisation of cellular automaton
    step functions using the :doc:`cagen <cagen>` module for Python and C++ code.
    *This allows running a synchronous automaton asynchronously without
    any change to the particular computation code.*
  - A GUI that's compatible with interactive usage through *IPythons* console,
    *qtconsole* and *notebook* web application.
  - Display configurations in one or two dimensions.
  - Show different types of *histograms*.
  - Manipulate cellular space through external programs, such as *The Gimp*,
    text editors like *Vim* and *Emacs* or using the full range of *numpy*
    from an interactive console.
  - An interactive tutorial for use with the *IPython notebook*.
  - A couple of *examples* with a walkthrough guiding the user through each.

Features that are currently in development in different branches are:

  - Define cells as composed of multiple subcells (*numpy-records branch*)
  - Turn any synchronous cellular automaton into an asynchronous automaton
    that still does the same computation.

Examples
========

Have a look at the :ref:`Example Gallery <screenshot_gallery>` for a few
interesting things zasim can do.

.. toctree::
    :hidden:

    gallery

Getting the code
================

The zasim code can be `found on github <http://github.com/timo/zasim/>`_.
Additionally, this documentation is built with "view source" links for
the files.

Running zasim
=============

Until using zasim in an interactive interpreter gets more convenient,
you can use the gui or cagen packages from the commandline. Both offer a
commandline argument interface with many different options. You can get a
usage summary with the following commands::

    zasim_cli --help

    zasim_gui --help

You can find :doc:`info on how to start the gui from the commandline <gui/main>`
and :doc:`how to start the commandline version <cagen/main>` with complete usage
summaries. There is also a section in the tutorial :ref:`about how to run the
commandline version <tutorial_invocation>`.

Environment variables
---------------------

`zasim` honors a few different environment variables during runtime:

`ZASIM_PY_DEBUG`
    Set this to "yes" to write out generated pure-python code path and filename
    when a StepFunc is generated, to "extreme" to create a print statement for
    every assignment in the python code. You can also set it to "pdb" or "pudb"
    to start a pdb or pudb when a StepFunc is stepped.

`ZASIM_WEAVE_DEBUG`
    Set this to "yes" to compile the C code with -O0 or to "gdb" to launch a gdb
    in "x-terminal-emulator" and have a trap signal be emitted every time a step
    is started.

`ZASIM_QT`
    Set this to "pyside" to use pyside or anything else to not use Qt at all.

.. seealso::

    :doc:`Debugging cagen stepfuncs <tutorial/debug_cagen>` goes deeper into how
    to use these environment variables to debug step functions.

Tutorial
========

This documentation contains a tutorial that guides you through usage of and
development with zasim.

.. toctree::
    :maxdepth: 2

    tutorial

Interactive Tutorial
--------------------

If you install the `ipython notebook`_ and its dependencies, you can run either
of the following commands

::

    zasim_tutorial

    python -m zasim.examples.notebooks.notebook_app

    ipython notebook --notebook-dir=zasim/examples/notebooks/notebooks/

to start zasim's interactive tutorial in a web browser.

.. _`ipython notebook`: http://ipython.org/ipython-doc/stable/install/install.html#dependencies-for-the-ipython-html-notebook

API Documentation
=================

.. toctree::
   :maxdepth: 2

   simulator
   config
   display
   cagen
   gui
   elementarytools

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

