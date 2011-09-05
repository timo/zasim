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
  - It runs fast, but developing fast cellular automatons is simple.

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

The code is not yet available on the 'net, but it be published soon.

Running zasim
=============

The main way to use zasim will in the future be to import the modules from
zasim in an interactive python interpreter, but that is currently not supported
very well. In order for the interactive mode to work well with the GUI, the GUI
will have to get its own thread.

Until then, you can just change the code at the bottom of zasim.cagen and
zasim.display, as well as zasim.elementarygui and invoke them with

::

    python -m zasim.display # for instance

from the console.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

