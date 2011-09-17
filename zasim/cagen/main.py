from .simulators import BinRule
from ..display.console import LinearConsolePainter
from ..features import HAVE_WEAVE

def test(width=75, copy_borders=True, rule=None, histogram=True, activity=False, pure=False, print_rule=True, nondet=100, beta=100, steps=100, base=2):

    beta = beta / 100.
    nondet = nondet / 100.

    bin_rule = BinRule((width,), rule=rule,
            histogram=histogram, activity=activity,
            nondet=nondet, beta=beta, copy_borders=copy_borders, base=base)

    display = LinearConsolePainter(bin_rule, 1)

    if print_rule:
        print bin_rule.pretty_print()

    if HAVE_WEAVE and not pure:
        print "weave"
        for i in range(steps):
            bin_rule.step_inline()
            if histogram:
                print bin_rule.t.histogram
            if activity:
                print bin_rule.t.activity
    else:
        print "pure"
        for i in range(steps):
            bin_rule.step_pure_py()
            if histogram:
                print bin_rule.t.histogram
            if activity:
                print bin_rule.t.activity

def main(args=None):
    import argparse

    argp = argparse.ArgumentParser(
        description="Run a generated BinRule simulator and display its results "
                    "on the console")
    argp.add_argument("-w", "--width", default=70, type=int,
            help="set the width of the configuration to calculate")
    argp.add_argument("-b", "--dont-copy-borders", default=True, dest="copy_borders", action="store_false",
            help="copy borders around. Otherwise, zeros will be read from "
                    "the borders")
    argp.add_argument("-r", "--rule", default=None, type=int,
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
    argp.add_argument("--base", default=2, type=int,
            help="The base of cell values. Base 2 gives you 0 and 1, for example.")

    args = argp.parse_args(args)

    test(**vars(args))


if __name__ == "__main__":
    main()
