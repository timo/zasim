:mod:`zasim.cagen` - Programmatically generating CAs
====================================================

Zasim offers a package for generating all the code needed to create and run a
step function without having to re-write boilerplate code. This is achieved by
offering a lot of re-usable components.

.. seealso::

    The tutorial section describes all classes involved in more detail and gives
    an example for how to make new Computation classes.

    You can start with :ref:`tutorial_stepfunc`.

This package also contains :doc:`pre-built simulators for commonly used cellular
automata <cagen/simulators>`.

When creating a new computation, you only need to write the core
computation once in C and once in python, the rest will be done for you by
the components offered in this module.

The parts the step function is decomposed into are all subclasses of
:class:`StepFuncVisitor`. The base classes available are:

:class:`CellLoop`
    defines the order in which to loop over the configuration cells.

:class:`StateAccessor`
    is responsible for writing to and reading from the configuration as
    well as knowing what shape and size the configuration has.

:class:`Neighbourhood`
    is responsible for getting the relevant fields for each local step.

:class:`BorderHandler`
    handles the borders of the configuration by copying over parts or writing
    data. Maybe, in the future, it could also resize configurations on demand.

:class:`Computation`
    handles the computation that turns the data from the neighbourhood into
    the result that goes into the value for the next step.

:class:`ExtraStats`
    compiles extra statistics, such as a histogram of the different cell states

All of those classes are used to initialise a :class:`StepFunc` object,
which can then target a configuration object with the method
:meth:`StepFunc.set_target`.

This package is split into multiple modules:

.. toctree::

    cagen/stepfunc
    cagen/bases
    cagen/loops
    cagen/accessors
    cagen/neighbourhoods
    cagen/border
    cagen/computations
    cagen/stats
    cagen/nondeterministic
    cagen/beta_async
    cagen/main
    cagen/simulators
    cagen/utils

.. note::

    The cagen package imports all classes from all submodules, so rather than writing

        >>> from zasim.cagen.loops import OneDimCellLoop

    you can also write

        >>> from zasim.cagen import OneDimCellLoop
