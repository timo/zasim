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

def test(width=75, copy_borders=True, rule=110, histogram=True, activity=False, pure=False, print_rule=True, nondet=100, beta=100, steps=100):

    beta = beta / 100.
    nondet = nondet / 100.

    bin_rule = BinRule((width,), rule=rule,
            histogram=histogram, activity=activity,
            nondet=nondet, beta=beta, copy_borders=copy_borders)

    b_l, b_r = bin_rule.stepfunc.neigh.bounding_box()[0]
    pretty_print_array = build_array_pretty_printer((width,), ((abs(b_l), abs(b_r)),), ((0, 0),))

    if print_rule:
        print bin_rule.pretty_print()


    if HAVE_WEAVE and not pure:
        print "weave"
        for i in range(steps):
            bin_rule.step_inline()
            pretty_print_array(bin_rule.cconf)
            if histogram:
                print bin_rule.histogram
            if activity:
                print bin_rule.activity
    else:
        print "pure"
        for i in range(steps):
            bin_rule.step_pure_py()
            pretty_print_array(bin_rule.cconf)
            if histogram:
                print bin_rule.histogram
            if activity:
                print bin_rule.activity

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

if __name__ == "__main__":
    import argparse

    argp = argparse.ArgumentParser(
        description="Run a generated BinRule simulator and display its results "
                    "on the console")
    argp.add_argument("-w", "--width", default=70, type=int,
            help="set the width of the configuration to calculate")
    argp.add_argument("-b", "--dont-copy-borders", default=True, dest="copy_borders", action="store_false",
            help="copy borders around. Otherwise, zeros will be read from "
                    "the borders")
    argp.add_argument("-r", "--rule", default=110, type=int,
            help="select the rule number to calculate")
    argp.add_argument("--histogram", default=False, action="store_true",
            help="calculate a histogram")
    argp.add_argument("--activity", default=False, action="store_true",
            help="calculate the activity")
    argp.add_argument("--pure", default=False, action="store_true",
            help="use pure python stepfunc even if weave is available")
    argp.add_argument("--print-rule", default=False, action="store_true",
            help="pretty-print the rule")
    argp.add_argument("-s", "--steps", metavar="STEPS", default=100, type=int,
            help="run the simulator for STEPS steps.")
    argp.add_argument("--nondet", default=100, type=int,
            help="with what percentage should cells be executed?")
    argp.add_argument("--beta", default=100, type=int,
            help="with what probability should a cell succeed in exposing its "\
                 "state to its neighbours?")

    args = argp.parse_args()

    test(**vars(args))
