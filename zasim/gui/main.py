from .display import ZasimDisplay
from .histogram import HistogramExtraDisplay

from ..external.qt import Qt, app
from .. import cagen
from ..simulator import CagenSimulator

import numpy as np
import sys

def main(width=200, height=200, scale=2,
        onedim=False,
        beta=100, nondet=100,
        life=False, rule=None, alt_rule=None,
        copy_borders=True, black=None,
        histogram=True, activity=True,
        base=2):

    if beta > 1:
        beta = beta / 100.
    if nondet > 1:
        nondet = nondet / 100.
    if black > 2:
        black = black / 100

    w, h = width, height
    if onedim:
        size = (w,)
    else:
        size = w, h

    if black is not None:
        rands = np.random.rand(*size)
        config = np.random.randint(0, base, size)
        config[rands < black] = 0

        size = None
    else:
        config = None

    print size, config

    if onedim and not life:
        if alt_rule is None:
            # get a random beautiful CA
            sim_obj = cagen.BinRule(rule=rule, size=size, config=config, nondet=nondet, beta=beta, activity=activity,
                    histogram=histogram, copy_borders=copy_borders, base=base)
        else:
            alt_rule = None if alt_rule == -1 else alt_rule
            compu = cagen.DualRuleCellularAutomaton(rule, alt_rule, nondet)
            sf_obj = cagen.automatic_stepfunc(size=size, config=config,
                    computation=compu, histogram=histogram, activity=activity,
                    copy_borders=copy_borders, base=base)
            sf_obj.gen_code()
            print compu.pretty_print()
            print compu.rule_a, compu.rule_b
            sim_obj = CagenSimulator(sf_obj, sf_obj.target)

    else:
        if life:
            sim_obj = cagen.GameOfLife(size, nondet, histogram, activity, config, beta, copy_borders)
        else:
            if alt_rule is None:
                sim_obj = cagen.ElementarySimulator(size, nondet, histogram, activity, rule, config, beta, copy_borders, base=base)
            else:
                alt_rule = None if alt_rule == -1 else alt_rule
                compu = cagen.DualRuleCellularAutomaton(rule, alt_rule, nondet)
                sf_obj = cagen.automatic_stepfunc(size=size, config=config,
                        computation=compu, histogram=histogram, activity=activity,
                        copy_borders=copy_borders, base=base)
                sf_obj.gen_code()
                print compu.pretty_print()
                print compu.rule_a, compu.rule_b
                sim_obj = CagenSimulator(sf_obj, sf_obj.target)

    if "rule" in sim_obj.target_attrs:
        print sim_obj.pretty_print()
        print sim_obj.t.rule, hex(sim_obj.rule_number)

    display = ZasimDisplay(sim_obj)
    display.set_scale(scale)

    display.control.start()

    if black is not None:
        display.control.zero_percentage.setValue(black)

    if histogram:
        extra_hist = HistogramExtraDisplay(sim_obj, parent=display, height=200, maximum= w * h)
        extra_hist.show()
        display.window.attach_display(extra_hist)
        display.window.addDockWidget(Qt.RightDockWidgetArea, extra_hist)

    if activity:
        extra_activity = HistogramExtraDisplay(sim_obj, attribute="activity", parent=display, height=200, maximum=w*h)
        extra_activity.show()
        display.window.attach_display(extra_activity)
        display.window.addDockWidget(Qt.RightDockWidgetArea, extra_activity)

    sys.exit(app.exec_())

def cli_main():
    import argparse

    argp = argparse.ArgumentParser(
        description="Run a 1d BinRule, a 2d Game of Life, or a 2d elementary "
                    "cellular automaton")
    argp.add_argument("--onedim", default=False, action="store_true",
            help="generate a one-dimensional cellular automaton")
    argp.add_argument("--twodim", default=True, action="store_false", dest="onedim",
            help="generate a two-dimensional cellular automaton")
    argp.add_argument("--life", default=False, action="store_true",
            help="generate a conway's game of life - implies --twodim")

    argp.add_argument("-x", "--width", default=200, dest="width", type=int,
            help="the width of the image surface")
    argp.add_argument("-y", "--height", default=200, dest="height", type=int,
            help="the height of the image surface")
    argp.add_argument("-z", "--scale", default=3, dest="scale", type=int,
            help="the size of each cell of the configuration")
    argp.add_argument("-r", "--rule", default=None, type=str,
            help="the elementary cellular automaton rule number to use")
    argp.add_argument("-R", "--alt-rule", default=None, type=str,
            help="the alternative rule to use. Supplying this will turn nondet into dual-rule mode")
    argp.add_argument("-c", "--dont-copy-borders", default=True, action="store_false", dest="copy_borders",
            help="copy borders or just read zeros?")
    argp.add_argument("--black", default=None, type=float,
            help="what percentage of the cells to make black at the beginning. (between 2 and 100 or 0.0 and 1.0)")

    argp.add_argument("--nondet", default=100, type=float,
            help="with what percentage should cells be executed? (either between 2 and 100 or 0.0 and 1.0)")
    argp.add_argument("--beta", default=100, type=float,
            help="with what probability should a cell succeed in exposing its "\
                 "state to its neighbours? (either between 2 and 100 or 0.0 and 1.0)")

    argp.add_argument("--no-histogram", default=True, action="store_false", dest="histogram",
            help="don't display a histogram")
    argp.add_argument("--no-activity", default=True, action="store_false", dest="activity",
            help="don't display the activity")
    argp.add_argument("--base", default=2, type=int,
            help="The base of the cells.")

    args = argp.parse_args()

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

    main(**vars(args))

if __name__ == "__main__":
    cli_main()
