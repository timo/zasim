from .display import ZasimDisplay
from .histogram import HistogramExtraDisplay

from ..external.qt import Qt
from .. import cagen

import sys

from zasim.cagen import *

class SillyComputation(Computation):
    def visit(self):
        self.code.add_py_hook("compute",
            """sup = max(%(name_one)s, %(name_two)s)
            second_sup = min(%(name_one)s, %(name_two)s)""" % dict(
                name_one=self.code.neigh.names[0],
                name_two=self.code.neigh.names[1]))
        # only create a loop if there are more than the 2 cells.
        if len(self.code.neigh.names) > 2:
            self.code.add_py_hook("compute",
                """
                for val in [%(names)s]:
                    if val > sup:
                        second_sup, sup = sup, val
                    elif val != sup and val > second_sup:
                        second_sup = val""" % dict(
                            names=",".join(self.code.neigh.names[2:])))
        # and finally, set the result value to be second_sup
        self.code.add_py_hook("compute",
            """result = second_sup""")

        # we need at least the sup and second_sup variables
        self.code.add_code("localvars",
            """int sup, second_sup;""")
        # initialise sup and second_sup from the first two neighbourhood cells
        self.code.add_code("compute",
            """
            if (%(name_one)s > %(name_two)s) {
                sup = %(name_one)s;
                second_sup = %(name_two)s;
            } else if (%(name_one)s < %(name_two)s) {
                sup = %(name_two)s;
                second_sup = %(name_one)s;
            } else {
                sup = %(name_one)s;
                second_sup = -1;
            }""" % dict(name_one=self.code.neigh.names[0],
                        name_two=self.code.neigh.names[1]))
        # if we have more neighbours, we simply loop over them
        if len(self.code.neigh.names) > 2:
            # in order to loop over the values in C, we create an array from them
            # the C compiler will probably completely optimise this away.
            self.code.add_code("localvars",
                    """int neigh_idx;""")
            self.code.add_code("compute",
                """int neigh_arr[%d] = {%s};""" % (len(self.code.neigh.names) - 2,
                                             ", ".join(self.code.neigh.names[2:])))
            self.code.add_code("compute",
                """
                for (neigh_idx = 0; neigh_idx < %(size)d; neigh_idx++) {
                    if (neigh_arr[neigh_idx] > sup) {
                        second_sup = sup;
                        sup = neigh_arr[neigh_idx];
                    } else if (neigh_arr[neigh_idx] > second_sup && neigh_arr[neigh_idx] < sup) {
                        second_sup = neigh_arr[neigh_idx];
                    }
                }""" % dict(size=len(self.code.neigh.names) - 2))
        self.code.add_code("compute",
           """if (second_sup != -1) {
                result = second_sup; }
            else {
                result = sup;}""")

class SillySim(CagenSimulator):
    def __init__(self, size=None, config=None, base=5, nondet=1, histogram=True, activity=False):
        if size is None:
            size = config.shape

        computer = SillyComputation()
        target = TestTarget(size, config, base=base)

        neighbourhood = VonNeumannNeighbourhood()
        acc = SimpleStateAccessor()
        if nondet != 1:
            loop = TwoDimNondeterministicCellLoop(nondet)
        else:
            loop = TwoDimCellLoop()
        border = TwoDimSlicingBorderCopier()

        stepfunc = StepFunc(
                loop=loop,
                accessor=acc,
                neighbourhood=neighbourhood,
                extra_code=[border, computer] +
                ([SimpleHistogram()] if histogram else []) +
                ([ActivityRecord()] if activity else []), target=target)
        self.computer = computer
        stepfunc.gen_code()

        super(SillySim, self).__init__(stepfunc, target)

    def pretty_print(self):
        return "foo"

def main(width=200, height=200, scale=2,
        onedim=False,
        beta=100, nondet=100,
        life=False, rule=None,
        copy_borders=True, white=50,
        histogram=True, activity=True,
        base=2):

    if white > 1:
        white = white / 100.

    beta = beta / 100.
    nondet = nondet / 100.

    w, h = width, height

    if onedim and not life:
        # get a random beautiful CA
        sim_obj = cagen.BinRule(rule=rule, size=(w,), nondet=nondet, beta=beta, activity=activity,
                histogram=histogram, copy_borders=copy_borders, base=base)

    else:
        if life:
            sim_obj = cagen.GameOfLife((w, h), nondet, histogram, activity, None, beta, copy_borders)
        else:
            #sim_obj = cagen.ElementarySimulator((w, h), nondet, histogram, activity, rule, None, beta, copy_borders, base=base)
            sim_obj = SillySim((w, h), base=base, nondet=nondet)

        #if not life:
            #print sim_obj.pretty_print()
            #print sim_obj.t.rule, hex(sim_obj.rule_number)

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
    argp.add_argument("--base", default=2, type=int,
            help="The base of the cells.")

    args = argp.parse_args()

    if args.rule:
        if args.rule.startswith("0x"):
            args.rule = int(args.rule, 16)
        else:
            args.rule = int(args.rule)

    main(**vars(args))
