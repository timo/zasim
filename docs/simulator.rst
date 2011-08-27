Common interface for Simulator classes
======================================

Simulator classes are derived from either PySide.QtCore.QObject,
PyQt.QtCore.QObject, so that the signals-and-slots mechanism can be used.

The module isn't dependent on Qt, though, as the lightweight_signal module
supplies a simple compatible Signal implementation.

.. automodule:: zasim.simulator
