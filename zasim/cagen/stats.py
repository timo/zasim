"""

"""
# This file is part of zasim. zasim is licensed under the BSD 3-clause license.
# See LICENSE.txt for details.

from .bases import ExtraStats
from .compatibility import histogram, activity

from ..features import HAVE_BINCOUNT

import numpy as np

class SimpleHistogram(ExtraStats):
    """Adding this class to the extra code list of a `StepFunc` will
    give access to a new array in the target called "histogram". This value will
    count the amount of cells with the value used as its index."""

    provides_features = [histogram]

    def visit(self):
        super(SimpleHistogram, self).visit()
        if len(self.code.acc.size_names) == 1:
            center_name = self.code.neigh.names[self.code.neigh.offsets.index((0,))]
        else:
            center_name = self.code.neigh.names[self.code.neigh.offsets.index((0, 0))]
        self.code.add_weave_code("post_compute",
                """if (result != %(center)s) { histogram(result) += 1; histogram(%(center)s) -= 1; }""" % dict(center=center_name))

        self.code.add_py_code("post_compute", """
            # update the histogram
            if result != %(center)s:
                self.target.histogram[result] += 1
                self.target.histogram[int(%(center)s)] -= 1""" % dict(center=center_name))

    def regenerate_histogram(self):
        conf = self.target.cconf
        acc = self.code.acc
        if len(acc.size_names) == 1:
            conf = conf[acc.border_size[acc.border_names[0][0]]:
                       -acc.border_size[acc.border_names[1][0]]]
        elif len(self.code.acc.size_names) == 2:
            conf = conf[acc.border_size[acc.border_names[0][0]]:
                       -acc.border_size[acc.border_names[1][0]],
                       acc.border_size[acc.border_names[0][1]]:
                       -acc.border_size[acc.border_names[1][1]]]
            # make the configuration 1d for bincount.
            conf = np.ravel(conf)
        else:
            raise NotImplementedError("Can only handle 1d or 2d arrays")
        # XXX this probably breaks down with paletted histograms?
        self.target.histogram = np.zeros(len(self.target.possible_values))
        if HAVE_BINCOUNT:
            histogram = np.bincount(conf)
        else:
            histogram = self.target.histogram
            for cell in conf:
                histogram[cell] += 1
        self.target.histogram[:len(histogram)] = histogram

    def new_config(self):
        """Create a starting histogram."""
        super(SimpleHistogram, self).new_config()
        self.regenerate_histogram()

    def init_once(self):
        """Set up the histogram attributes."""
        super(SimpleHistogram, self).init_once()
        self.code.attrs.extend(["histogram"])

    def build_name(self, parts):
        parts.append("(histogram)")

class ActivityRecord(ExtraStats):
    """Adding this class to the extra code list of a `StepFunc` will
    create a property called "activity" on the target. It is a two-cell
    array with the value of how many fields have changed their state in the last
    step and how many did not.

    A value of -1 stands for "no data".

    Additionally, the local variable `was_active` is available after post_compute."""

    provides_features = [activity]

    def visit(self):
        super(ActivityRecord, self).visit()
        if len(self.code.acc.size_names) == 1:
            center_name = self.code.neigh.names[self.code.neigh.offsets.index((0,))]
        else:
            center_name = self.code.neigh.names[self.code.neigh.offsets.index((0, 0))]

        self.code.add_weave_code("localvars",
                """activity(1) = 0; bool was_active;""")
        self.code.add_weave_code("post_compute",
                """was_active = result != %(center)s;
                   if (was_active) { activity(1) += 1; }""" % dict(center=center_name))

        self.code.add_weave_code("after_step",
                """activity(0) = cell_count - activity(1);""")

        self.code.add_py_code("init",
                """self.target.activity[1] = 0;""")
        self.code.add_py_code("post_compute", """
            # count up the activity
            was_active = result != %(center)s
            if was_active:
                self.target.activity[1] += 1"""
                % dict(center=center_name))

        self.code.add_py_code("after_step",
                """self.target.activity[0] = cell_count - self.target.activity[1]""")

    def new_config(self):
        """Reset the activity counter to -1, which stands for "no data"."""
        super(ActivityRecord, self).new_config()
        self.target.activity = np.array([-1, -1])

    def init_once(self):
        """Set up the activity attributes."""
        super(ActivityRecord, self).init_once()
        self.code.attrs.extend(["activity"])

    def build_name(self, parts):
        parts.append("(activity)")

