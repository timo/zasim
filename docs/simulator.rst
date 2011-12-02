Common interface for Simulator classes
======================================

Simulator classes are derived from either PySide.QtCore.QObject,
PyQt.QtCore.QObject, so that the signals-and-slots mechanism can be used.

.. seealso::

    The tutorial section handles the :ref:`simulator <tutorial_stepfunc_simulator>`
    and :ref:`target <tutorial_stepfunc_target>` classes in more
    detail in :ref:`the tutorial about creating custom StepFunc objects
    <tutorial_stepfunc>`

.. automodule:: zasim.simulator

Using Simulator without Qt
--------------------------

The module isn't dependent on Qt, as the lightweight_signal module
supplies a simple compatible Signal implementation.

.. automodule:: zasim.lightweight_signal
