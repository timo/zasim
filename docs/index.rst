Welcome to zasim
================

zasim is a python package for simulating and developing cellular automatons.

When in a more finished state, its main features will be:

  - Reduction of boilerplate code by using the :doc:`cagen <cagen>` module.
  - User interface tightly coupled with interactive console. Generate
    transscripts of sessions and re-play them.
  - Displaying one-dimensional and two-dimensional cellular automatons.
  - Show different types of histograms.
  - Compare different runs of cellular automatons.
  - Manipulate cellular space through UI or code.
  - It runs fast, but developing new cellular automatons is simple.

Contents:

.. toctree::
   :maxdepth: 2

   simulator
   ca
   cagen
   display
   elementarytools
   elementarygui

Getting the code
================

The code is not yet available on the 'net, due to licensing questions that
still require resolving.

Running zasim
=============

The main way to use zasim will in the future be to import the modules from
zasim in an interactive python interpreter, but that is currently not
supported by the gui very well. In order for the interactive mode to work
well with the GUI, the GUI will have to get its own thread.

Until then, you can use the display or cagen module from the commandline.
Both offer a commandline argument interface with many different options.
You can get a usage summary with the following commands:

::

    python -m zasim.display --help
    python -m zasim.cagen --help

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

