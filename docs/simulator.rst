Common interface for Simulator classes
======================================

Simulator classes are derived from either PySide.QtCore.QObject,
PyQt.QtCore.QObject, so that the signals-and-slots mechanism can be used.

.. automodule:: zasim.simulator

Using Simulator without Qt
--------------------------

The module isn't dependent on Qt, as the lightweight_signal module
supplies a simple compatible Signal implementation.

.. automodule:: zasim.lightweight_signal
