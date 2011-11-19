from .bases import CellLoop
from .compatibility import one_dimension, two_dimensions

import numpy as np

class OneDimCellLoop(CellLoop):
    """The OneDimCellLoop iterates over all cells in order from 0 to sizeX."""

    requires_features = [one_dimension]

    def get_pos(self):
        return "i"

    def visit(self):
        super(OneDimCellLoop, self).visit()
        self.code.add_code("loop_begin",
                """for(int i=0; i < sizeX; i++) {""")
        self.code.add_code("loop_end",
                """}""")

    def get_iter(self):
        def generator():
            for i in range(0, self.code.acc.get_size_of()):
                yield (i,)
        return iter(generator())

    def build_name(self, parts):
        parts.insert(0, "1d")

class TwoDimCellLoop(CellLoop):
    """The TwoDimCellLoop iterates over all cells from left to right, then from
    top to bottom."""

    requires_features = [two_dimensions]

    def get_pos(self):
        return "i", "j"

    def visit(self):
        super(TwoDimCellLoop, self).visit()
        size_names = self.code.acc.size_names
        self.code.add_code("loop_begin",
            """for(int i=0; i < %s; i++) {
                for(int j=0; j < %s; j++) {""" % (size_names))
        self.code.add_code("loop_end",
                """}
                }""")

    def get_iter(self):
        def iterator():
            for i in range(0, self.code.acc.get_size_of(0)):
                for j in range(0, self.code.acc.get_size_of(1)):
                    yield (i, j)
        return iter(iterator())

    def build_name(self, parts):
        parts.insert(0, "2d")

class SparseCellLoopBase(CellLoop):
    """The SparseCellLoopBase offers common code for loops that only calculate
    those fields, where the neighbours have changed in the last step.

    This is based on a list of positions called `sparse_list` as well as a mask
    of booleans called `sparse_mask`, that only internally gets used to make
    sure, that no fields are enlisted more than once."""

    def set_target(self, target):
        """Adds the activity mask and position list to the target attributes."""
        super(SparseCellLoopBase, self).set_target(target)

        size = self.calculate_size()
        target.sparse_mask = np.zeros(size, dtype=np.bool)
        target.sparse_list = np.zeros(size, dtype=np.int)

    def calculate_size(self):
        """Calculate how big the mask and list have to be.

        The current strategy is to just allocate one field for each field of the
        configuration."""
        return reduce(lambda a, b: a * b, self.target.size)

