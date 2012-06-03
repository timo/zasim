"""

"""
# This file is part of zasim. zasim is licensed under the BSD 3-clause license.
# See LICENSE.txt for details.

from .. import external

external.WANT_GUI = False

from .simulators import BinRule, GameOfLife
from ..simulator import CagenSimulator
from ..display.console import OneDimConsolePainter, TwoDimConsolePainter
from ..features import HAVE_WEAVE
from ..config import PatternConfiguration
from . import DualRuleCellularAutomaton, automatic_stepfunc

from ..debug import launch_debugger

import os

def test(width=75, height=None, life=False, copy_borders=True,
         rule=None, alt_rule=None,
         histogram=True, activity=False,
         pure=False, print_rule=True,
         nondet=100, beta=100, steps=100, base=2,
         sparse=False, background=None, patterns=None, layout=None):

    if beta > 1.0:
        beta = beta / 100.
    if nondet > 1.0:
        nondet = nondet / 100.

    if life:
        assert (background, patterns, layout) == (None, None, None), "cannot use pattern generator with game of life"
        if height is None:
            height = 40
        sim_obj = GameOfLife((width, height), nondet, histogram, activity, None, beta, copy_borders, sparse_loop=sparse)
    else:
        size = (width,) if height is None else (width, height)

        if any((background, patterns, layout)):
            config = PatternConfiguration([background or [0]] + (patterns or [[1]]), layout or [1])
        else:
            config = None

        if alt_rule is None:
            sim_obj = BinRule(size=size, config=config, rule=rule,
                    histogram=histogram, activity=activity,
                    nondet=nondet, beta=beta, copy_borders=copy_borders, base=base, sparse_loop=sparse)
        else:
            compu = DualRuleCellularAutomaton(rule, alt_rule, nondet)
            sf_obj = automatic_stepfunc(size,
                    computation=compu, histogram=histogram, activity=activity,
                    copy_borders=copy_borders, base=base, sparse_loop=sparse,
                    needs_random_generator=True)
            sf_obj.gen_code()
            sim_obj = CagenSimulator(sf_obj, sf_obj.target)

    if height is None:
        display = OneDimConsolePainter(sim_obj, 1)
    else:
        display = TwoDimConsolePainter(sim_obj)
        def extra_newline():
            print
        sim_obj.updated.connect(extra_newline)

    if print_rule:
        print sim_obj.pretty_print()
        print sim_obj.rule_number, "==", hex(sim_obj.rule_number)

    if os.environ.get("ZASIM_WEAVE_DEBUG", False) == "gdb":
        launch_debugger()

    if HAVE_WEAVE and not pure:
        for i in xrange(steps):
            sim_obj.step_inline()
            if histogram:
                print sim_obj.t.histogram
            if activity:
                print sim_obj.t.activity, sum(sim_obj.t.activity)
    else:
        for i in xrange(steps):
            sim_obj.step_pure_py()
            if histogram:
                print sim_obj.t.histogram
            if activity:
                print sim_obj.t.activity, sum(sim_obj.t.activity)

def main(args=None):
    import argparse

    def parse_intlist(text):
        if " " not in text and "," not in text:
            return map(int, text)
        import re
        return re.findall(r"\d+", text)

    argp = argparse.ArgumentParser(
        description="Run a generated BinRule simulator and display its results "
                    "on the console")
    argp.add_argument("-x", "--width", default=70, type=int,
            help="set the width of the configuration to calculate")
    argp.add_argument("-y", "--height", default=None, type=int,
            help="set the height of the configuration to calculate")
    argp.add_argument("-b", "--dont-copy-borders", default=True, dest="copy_borders", action="store_false",
            help="copy borders around. Otherwise, zeros will be read from "
                    "the borders")
    argp.add_argument("-r", "--rule", default=None, type=str,
            help="select the rule number to calculate")
    argp.add_argument("-R", "--alt-rule", default=None, type=str,
            help="the alternative rule to use. Supplying this will turn nondet into dual-rule mode")
    argp.add_argument("--histogram", default=False, action="store_true",
            help="calculate a histogram")
    argp.add_argument("--activity", default=False, action="store_true",
            help="calculate the activity")
    argp.add_argument("--pure", default=False, action="store_true",
            help="use pure python stepfunc even if weave is available")
    argp.add_argument("--print-rule", default=False, action="store_true",
            help="pretty-print the rule")
    argp.add_argument("--life", default=False, action="store_true",
            help="calculate a game of life.")
    argp.add_argument("-s", "--steps", metavar="STEPS", default=100, type=int,
            help="run the simulator for STEPS steps.")
    argp.add_argument("--nondet", default=100, type=float,
            help="with what percentage should cells be executed? (either between 2 and 100 or between 0.0 and 1.0)")
    argp.add_argument("--beta", default=100, type=float,
            help="with what probability should a cell succeed in exposing its "\
                 "state to its neighbours? (either between 2 and 100 or between 0.0 and 1.0)")
    argp.add_argument("--base", default=2, type=int,
            help="The base of cell values. Base 2 gives you 0 and 1, for example.")

    argp.add_argument("--sparse", default=False, type=bool,
            help="Should a sparse loop be generated?")

    argp.add_argument("--background", type=parse_intlist,
            help="What background pattern should be generated?")
    argp.add_argument("--pattern", type=parse_intlist, action="append", dest="patterns",
            help="Add a pattern to the available patterns for the layout.")
    argp.add_argument("--layout", type=parse_intlist, 
            help="What combinations of patterns to put in the middle.")


    args = argp.parse_args(args)

    if args.rule:
        if args.rule.startswith("0x"):
            args.rule = int(args.rule, 16)
        else:
            args.rule = int(args.rule)
    if args.alt_rule:
        if args.alt_rule.startswith("0x"):
            args.alt_rule = int(args.alt_rule, 16)
        else:
            args.alt_rule = int(args.alt_rule)

    test(**vars(args))


if __name__ == "__main__":
    main()
