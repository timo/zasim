from .display import ZasimDisplay
from .histogram import HistogramExtraDisplay

from ..external.qt import QApplication, Qt
from .. import cagen

import sys
import random

def main(width=200, height=200, scale=2,
        onedim=False,
        beta=100, nondet=100,
        life=False, rule=None,
        copy_borders=True, white=50,
        histogram=True, activity=True):
    app = QApplication(sys.argv)

    if white > 1:
        white = white / 100.

    beta = beta / 100.
    nondet = nondet / 100.

    w, h = width, height

    if onedim and not life:
        # get a random beautiful CA
        if rule is None:
            rule=random.choice(
             [22, 26, 30, 45, 60, 73, 90, 105, 110, 122, 106, 150])

        sim_obj = cagen.BinRule(rule=rule, size=(w,), nondet=nondet, beta=beta, activity=activity,
                histogram=histogram, copy_borders=copy_borders)

    else:
        if life:
            sim_obj = cagen.GameOfLife((w, h), nondet, histogram, activity, None, beta, copy_borders)
        else:
            sim_obj = cagen.ElementarySimulator((w, h), nondet, histogram, activity, rule, None, beta, copy_borders)

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
    argp.add_argument("-r", "--rule", default=None, type=int,
            help="the elementary cellular automaton rule number to use")
    argp.add_argument("-c", "--dont-copy-borders", default=True, action="store_false", dest="copy_borders",
            help="copy borders or just read zeros?")
    argp.add_argument("--white", default=20, type=int,
            help="what percentage of the cells to make white at the beginning.")

    argp.add_argument("--nondet", default=100, type=int,
            help="with what percentage should cells be executed?")
    argp.add_argument("--beta", default=100, type=int,
            help="with what probability should a cell succeed in exposing its "\
                 "state to its neighbours?")

    argp.add_argument("--no-histogram", default=True, action="store_false", dest="histogram",
            help="don't display a histogram")
    argp.add_argument("--no-activity", default=True, action="store_false", dest="activity",
            help="don't display the activity")

    args = argp.parse_args()

    main(**vars(args))


    if len(sys.argv) > 1:
        if sys.argv[1].startswith("0x"):
            rule_nr = int(sys.argv[1], 16)
        else:
            rule_nr = int(sys.argv[1])
        main(rule_nr)
    else:
        main()