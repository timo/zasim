from .display import ZasimDisplay
from .histogram import HistogramExtraDisplay
from .argp_qt import make_argument_parser

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
        base=2, sparse=False):

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
                    histogram=histogram, copy_borders=copy_borders, base=base, sparse_loop=sparse)
        else:
            alt_rule = None if alt_rule == -1 else alt_rule
            compu = cagen.DualRuleCellularAutomaton(rule, alt_rule, nondet)
            sf_obj = cagen.automatic_stepfunc(size=size, config=config,
                    computation=compu, histogram=histogram, activity=activity,
                    copy_borders=copy_borders, base=base,
                    needs_random_generator=True)
            sf_obj.gen_code()
            print compu.pretty_print()
            print compu.rule_a, compu.rule_b
            sim_obj = CagenSimulator(sf_obj, sf_obj.target)

    else:
        if life:
            sim_obj = cagen.GameOfLife(size, nondet, histogram, activity, config, beta, copy_borders, sparse_loop=sparse)
        else:
            if alt_rule is None:
                sim_obj = cagen.ElementarySimulator(size, nondet, histogram, activity, rule, config, beta, copy_borders, base=base, sparse_loop=sparse)
            else:
                alt_rule = None if alt_rule == -1 else alt_rule
                compu = cagen.DualRuleCellularAutomaton(rule, alt_rule, nondet)
                sf_obj = cagen.automatic_stepfunc(size=size, config=config,
                        computation=compu, histogram=histogram, activity=activity,
                        copy_borders=copy_borders, base=base,
                        needs_random_generator=True, sparse_loop=sparse)
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
    argp = make_argument_parser()

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
