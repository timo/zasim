.. _display-package:

:mod:`zasim.display` - Package for displaying configs
=====================================================

This package offers functionality to display the configs of simulators in
different formats. At the moment, there are display methods for images based on
QImage and for ascii art. Both can handle arbitrary field values, if the right
palette is supplied.

For interactive use with IPython, the QImage based renderers offer embedding
their images into the shell as PNG images and the console based renderers offer
rendering as HTML tables.

.. toctree::

    display/qt
    display/console

