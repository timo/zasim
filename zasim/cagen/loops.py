from .bases import CellLoop
from .compatibility import one_dimension, two_dimensions, activity
from .utils import offset_pos

from itertools import product
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

class SparseCellLoop(CellLoop):
    """The SparseCellLoopBase offers common code for loops that only calculate
    those fields, where the neighbours have changed in the last step.

    This is based on a list of positions called `sparse_list` as well as a mask
    of booleans called `sparse_mask`, that only internally gets used to make
    sure, that no fields are enlisted more than once.

    The `sparse_list` is duplicated into the property `prev_sparse_list`, from
    which reads are performed. Additionally, the number of active cells is
    taken from an "activity" stats before the loop to see how many valid
    entries exist in the array.

    For the pure-py version, a normal python set is used."""

    requires_features = [activity]

    def set_target(self, target):
        """Adds the activity mask and position list to the target attributes."""
        super(SparseCellLoop, self).set_target(target)

        if len(target.size) == 1:
            self.requires_features.append(one_dimension)
        elif len(target.size) == 2:
            self.requires_features.append(two_dimensions)
        else:
            raise NotImplementedError("SparseCellLoop has not been modified to"
                    " work with more than 2 dimensions.")

        size = self.calculate_size()
        target.sparse_mask = np.zeros(size, dtype=np.bool)
        target.sparse_list = np.zeros(size, dtype=np.int)
        target.sparse_set = set()

    def get_pos(self):
        return self.position_names

    def calculate_size(self):
        """Calculate how big the mask and list have to be.

        The current strategy is to just allocate one field for each field of the
        configuration."""
        return reduce(lambda a, b: a * b, self.target.size)

    def mark_cell_py(self, pos):
        positions = [offset_pos(pos, offs) for offs in
                     self.code.neigh.affected_cells()]
        positions = [pos
                         if self.code.border.is_position_valid(pos)
                         else self.code.border.correct_position(pos)
                     for pos in positions]
        self.target.sparse_set.update(positions)

    def new_config(self):
        size = self.calculate_size()
        self.target.sparse_mask = np.ones(size, dtype=np.bool)
        self.target.sparse_list = np.array(range(size), dtype=np.int)
        self.target.prev_sparse_list = self.target.sparse_list.copy()
        self.target.sparse_set = set(product(*[range(siz) for siz in self.target.size]))

    def get_iter(self):
        # iterate over a copy of the set, so that it can be modified while running
        print len(self.target.sparse_set)
        the_list = list(self.target.sparse_set)
        self.target.sparse_set.clear()
        return iter(the_list)

    def visit(self):
        print "the sparse cell loop is being visited"
        super(SparseCellLoop, self).visit()
        self.code.add_py_hook("loop_end",
            """if was_active: self.loop.mark_cell_py(pos)""")
        #self.code.add_code("loop_begin",
            #"""int valid_positions = activity(1);
               #for(int i=0; i < %s; i++) {
                  #)
        #self.code.add_code("loop_end",
                #"""}
                #}""") 

class OneDimSparseCellLoop(SparseCellLoop):
    def __init__(self):
        self.position_names = "i"

class TwoDimSparseCellLoop(SparseCellLoop):
    def __init__(self):
        self.position_names = "i", "j"
