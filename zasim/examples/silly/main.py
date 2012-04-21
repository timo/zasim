"""

"""
# {LICENSE_TEXT}
from zasim.gui.display import ZasimDisplay
from zasim.gui.histogram import HistogramExtraDisplay

from zasim.external.qt import Qt, app
from zasim import cagen

import numpy as np

import sys

class SillyComputation(cagen.bases.Computation):
    def visit(self):
        self.code.add_py_code("compute",
            """sup = max(%(name_one)s, %(name_two)s)
            second_sup = min(%(name_one)s, %(name_two)s)""" % dict(
                name_one=self.code.neigh.names[0],
                name_two=self.code.neigh.names[1]))
        # only create a loop if there are more than the 2 cells.
        if len(self.code.neigh.names) > 2:
            self.code.add_py_code("compute",
                """
                for val in [%(names)s]:
                    if val > sup:
                        second_sup, sup = sup, val
                    elif val > second_sup:
                        second_sup = val""" % dict(
                            names=",".join(self.code.neigh.names[2:])))
        # and finally, set the result value to be second_sup
        self.code.add_py_code("compute",
            """result = second_sup""")

        # we need at least the sup and second_sup variables
        self.code.add_weave_code("localvars",
            """int sup, second_sup;""")
        # initialise sup and second_sup from the first two neighbourhood cells
        self.code.add_weave_code("compute",
            """
            if (%(name_one)s > %(name_two)s) {
                sup = %(name_one)s;
                second_sup = %(name_two)s;
            } else {
                sup = %(name_two)s;
                second_sup = %(name_one)s;
            }""" % dict(name_one=self.code.neigh.names[0],
                        name_two=self.code.neigh.names[1]))
        # if we have more neighbours, we simply loop over them
        if len(self.code.neigh.names) > 2:
            # in order to loop over the values in C, we create an array from them
            # the C compiler will probably completely optimise this away.
            self.code.add_weave_code("localvars",
                    """int neigh_idx;""")
            self.code.add_weave_code("compute",
                """int neigh_arr[%d] = {%s};""" % (len(self.code.neigh.names) - 2,
                                             ", ".join(self.code.neigh.names[2:])))
            self.code.add_weave_code("compute",
                """
                for (neigh_idx = 0; neigh_idx < %(size)d; neigh_idx++) {
                    if (neigh_arr[neigh_idx] > sup) {
                        second_sup = sup;
                        sup = neigh_arr[neigh_idx];
                    } else if (neigh_arr[neigh_idx] > second_sup) {
                        second_sup = neigh_arr[neigh_idx];
                    }
                }""" % dict(size=len(self.code.neigh.names) - 2))
        self.code.add_weave_code("compute",
           """result = second_sup;""")

class SillySim(cagen.simulators.CagenSimulator):
    def __init__(self, size=None, config=None, base=5, nondet=1, beta=1, copy_borders=True, histogram=True, activity=False):
        if size is None:
            size = config.shape

        computer = SillyComputation()
        neighbourhood = cagen.neighbourhoods.VonNeumannNeighbourhood

        stepfunc = cagen.simulators.automatic_stepfunc(size=size, config=config, computation=computer,
                nondet=nondet, beta=beta,
                histogram=histogram, activity=activity,
                copy_borders=copy_borders, neighbourhood=neighbourhood,
                base=base, extra_code=[])
        self.computer = computer
        self.target = stepfunc.target
        stepfunc.gen_code()

        print stepfunc.code_text

        super(SillySim, self).__init__(stepfunc)

    def pretty_print(self):
        return "foo"

def main(width=200, height=200, scale=2,
        beta=100, nondet=100,
        copy_borders=True, black=80,
        histogram=True, activity=True,
        base=7):

    beta = beta / 100.
    nondet = nondet / 100.

    w, h = width, height
    size = w, h

    if black is not None:
        rands = np.random.rand(*size)
        config = np.random.randint(0, base, size)
        config[rands < black] = 0

        size = None
    else:
        config = None

    sim_obj = SillySim(size=size, config=config, base=base, nondet=nondet, histogram=histogram, activity=activity, beta=beta, copy_borders=copy_borders)

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
        description="Run the 'silly computation' example in a gui.")
    argp.add_argument("-x", "--width", default=200, dest="width", type=int,
            help="the width of the image surface")
    argp.add_argument("-y", "--height", default=200, dest="height", type=int,
            help="the height of the image surface")
    argp.add_argument("-z", "--scale", default=3, dest="scale", type=int,
            help="the size of each cell of the configuration")
    argp.add_argument("-c", "--dont-copy-borders", default=True, action="store_false", dest="copy_borders",
            help="copy borders or just read zeros?")
    argp.add_argument("--black", default=80, type=int,
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
            help="How many colors to have.")

    args = argp.parse_args()

    main(**vars(args))
