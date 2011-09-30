from .display import ZasimDisplay
from .histogram import HistogramExtraDisplay

from ..external.qt import Qt, app
from .. import cagen

import numpy as np
import sys

def main(width=200, height=200, scale=2,
        onedim=False,
        beta=100, nondet=100,
        life=False, rule=None,
        copy_borders=True, black=None,
        histogram=True, activity=True,
        base=2):
    if black > 1:
        black = black / 100.

    beta = beta / 100.
    nondet = nondet / 100.

    w, h = width, height
    if onedim:
        size = (w,)
    else:
        size = w, h

    if black is not None:
        print size, base
        rands = np.random.rand(*size)
        config = np.random.randint(0, base, size)
        config[rands < black] = 0

        size = None
    else:
        config = None

    print size, config

    if onedim and not life:
        # get a random beautiful CA
        sim_obj = cagen.BinRule(rule=rule, size=size, config=config, nondet=nondet, beta=beta, activity=activity,
                histogram=histogram, copy_borders=copy_borders, base=base)

    else:
        if life:
            sim_obj = cagen.GameOfLife(size, nondet, histogram, activity, config, beta, copy_borders)
        else:
            sim_obj = cagen.ElementarySimulator(size, nondet, histogram, activity, rule, config, beta, copy_borders, base=base)

    if not life:
        print sim_obj.pretty_print()
        print sim_obj.t.rule, hex(sim_obj.rule_number)

    display = ZasimDisplay(sim_obj)
    display.set_scale(scale)

    display.control.start()

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

if __name__ == "__main__":
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
    argp.add_argument("-c", "--dont-copy-borders", default=True, action="store_false", dest="copy_borders",
            help="copy borders or just read zeros?")
    argp.add_argument("--black", default=None, type=int,
            help="what percentage of the cells to make black at the beginning.")

    argp.add_argument("--nondet", default=100, type=int,
            help="with what percentage should cells be executed?")
    argp.add_argument("--beta", default=100, type=int,
            help="with what probability should a cell succeed in exposing its "\
                 "state to its neighbours?")

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

    main(**vars(args))
