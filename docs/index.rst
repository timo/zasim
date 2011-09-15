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

Getting the code
================

The code is not yet available on the 'net, due to licensing questions that
still require resolving.

Running zasim
=============

Until using zasim in an interactive interpreter gets more convenient,
you can use the gui or cagen packages from the commandline. Both offer a
commandline argument interface with many different options. You can get a
usage summary with the following commands:

You can find :doc:`info on how to start the gui from the commandline <gui/main>`
and :doc:`how to start the commandline version <cagen/main>` with complete usage
summaries.


API Documentation
=================

.. toctree::
   :maxdepth: 2

   simulator
   display
   cagen
   gui
   elementarytools

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

