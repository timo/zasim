# coding: utf-8
"""This module offers the ability to slim down the specification of
cellular automaton step functions using re-usable components.

You only need to write the core computation once in C and once in python,
the rest will be done for you by the components offered in this module.

The parts the step function is decomposed into are all subclasses of
:class:`WeaveStepFuncVisitor`. The base classes available are:

  - A :class:`StateAccessor`

    is responsible for writing to and reading from the configuration as
    well as knowing what shape and size the configuration has.

  - A :class:`CellLoop`

    defines the order in which to loop over the configuration cells.

  - A :class:`Neighbourhood`

    is responsible for getting the relevant fields for each local step.

  - A :class:`BorderHandler`

    handles the borders of the configuration by copying over parts or writing
    data. Maybe, in the future, it could also resize configurations on demand.

  - A :class:`Computation`

    handles the computation that turns the data from the neighbourhood into
    the result that goes into the value for the next step.

All of those classes are used to initialise a :class:`WeaveStepFunc` object,
which can then target a configuration object with the method
:meth:`~WeaveStepFunc.set_target`.

.. testsetup:: *

    from zasim.cagen import *
"""

# TODO make it extra hard to change the loop variables using a neighbourhood.

# TODO separate the functions to make C code from the ones that do pure python
#      computation

# TODO figure out how the code should handle resizing of configurations and
#      other such things.

# TODO figure out if scipy.weave.accelerate_tools is any good.

from .accessors import *
from .bases import *
from .beta_async import *
from .border import *
from .computations import *
from .loops import *
from .neighbourhoods import *
from .nondeterministic import *
from .simulators import *
from .stats import *
from .stepfunc import *
from .target import *

def categories():
    all_classes = []
    categories = {}
    look_at = WeaveStepFuncVisitor.__subclasses__()

    while len(look_at) > 0:
        item = look_at.pop()
        if item.category not in categories:
            categories[item.category] = []
        categories[item.category].append(item)
        all_classes.append(item)
        look_at.extend([cls for cls in item.__subclasses__() if cls not in all_classes])

    return categories

