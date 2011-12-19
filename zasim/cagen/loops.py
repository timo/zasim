"""

{LICENSE_TEXT}
"""
from .bases import CellLoop
from .compatibility import one_dimension, two_dimensions, activity, random_generator
from .utils import offset_pos

from itertools import product, izip
import numpy as np

class OneDimCellLoop(CellLoop):
    """The OneDimCellLoop iterates over all cells in order from 0 to sizeX."""

    requires_features = [one_dimension]

    def get_pos(self):
        return "loop_x",

    def visit(self):
        super(OneDimCellLoop, self).visit()
        self.code.add_code("loop_begin",
                """for(int loop_x=0; loop_x < sizeX; loop_x++) {""")
        self.code.add_code("loop_end",
                """}""")

    def get_iter(self):
        return iter(izip(xrange(0, self.code.acc.get_size_of(0))))

    def build_name(self, parts):
        parts.insert(0, "1d")

class TwoDimCellLoop(CellLoop):
    """The TwoDimCellLoop iterates over all cells from left to right, then from
    top to bottom."""

    requires_features = [two_dimensions]

    def get_pos(self):
        return "loop_x", "loop_y"

    def visit(self):
        super(TwoDimCellLoop, self).visit()
        size_names = self.code.acc.size_names
        self.code.add_code("loop_begin",
            """for(int loop_x=0; loop_x < %s; loop_x++) {
                for(int loop_y=0; loop_y < %s; loop_y++) {""" % (size_names))
        self.code.add_code("loop_end",
                """}
                }""")

    def get_iter(self):
        return iter(product(xrange(0, self.code.acc.get_size_of(0)),
                            xrange(0, self.code.acc.get_size_of(1))))

    def build_name(self, parts):
        parts.insert(0, "2d")

class SparseCellLoop(CellLoop):
    """The SparseCellLoop offers common code for loops that only calculate
    those fields, where the neighbours have changed in the last step.

    This is based on a list of positions called `sparse_list` as well as a mask
    of booleans called `sparse_mask`, that only internally gets used to make
    sure, that no fields are enlisted more than once.

    The `sparse_list` is duplicated into the property `prev_sparse_list`, from
    which reads are performed. All entries in the sparse_list arrays are valid
    up to the first -1.

    For the pure-py version, a normal python set is used.

    It requires an ActivityRecord for the `was_active` flag."""

    probab = None

    def set_target(self, target):
        """Adds the activity mask and position list to the target attributes."""
        super(SparseCellLoop, self).set_target(target)

        size = self.calculate_size()
        target.sparse_mask = np.zeros(size, dtype=bool)
        target.sparse_list = np.zeros(size, dtype=int)
        target.sparse_set = set()

    def bind(self, code):
        super(SparseCellLoop, self).bind(code)
        if self.probab is not None:
            code.consts["NONDET_PROBAB"] = self.probab

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
        self.target.sparse_mask = np.ones(size, dtype=bool)
        self.target.sparse_list = np.array(list(range(size)) + [-1] , dtype=int)
        self.target.prev_sparse_list = self.target.sparse_list.copy()
        self.target.sparse_set = set(product(*[range(siz) for siz in self.target.size]))

    def get_iter(self):
        # iterate over a copy of the set, so that it can be modified while running
        the_list = list(self.target.sparse_set)
        self.target.sparse_set.clear()
        if self.probab is not None:
            # get a list of entries to go through
            sublist = []
            for pos in the_list:
                if self.code.random.random() >= self.probab:
                    sublist.append(pos)
                else:
                    self.target.sparse_set.update([pos])
            return iter(sublist)
        else:
            return iter(the_list)

    def visit(self):
        super(SparseCellLoop, self).visit()

        self.code.attrs.append("sparse_mask")
        self.code.attrs.append("sparse_list")
        self.code.attrs.append("prev_sparse_list")

        self.code.add_py_hook("loop_end",
            """if was_active: self.loop.mark_cell_py(pos)""")

        self.code.add_code("localvars",
            """int sparse_cell_write_idx = 0;""")

        # copy all data over, because of the inactive cells.
        self.code.add_code("localvars",
            """nconf = cconf.copy();""")

        self.code.add_code("loop_begin",
            """for(int cell_idx=0; prev_sparse_list(cell_idx) != -1; cell_idx++) {""")
        if self.probab is not None:
            self.code.add_code("loop_begin",
                """if(rand() >= RAND_MAX * NONDET_PROBAB) {
                    if(!sparse_mask(cell_idx)) {
                        sparse_list(sparse_cell_write_idx) = cell_idx;
                        sparse_mask(cell_idx) = true;
                        sparse_cell_write_idx++;
                    }
                    continue;
                }""")
        if len(self.position_names) == 1:
            self.code.add_code("loop_begin",
                """    int %s = prev_sparse_list(cell_idx);""" % self.position_names)
        elif len(self.position_names) == 2:
            self.code.add_code("loop_begin",
                """    int %(pos_a)s = prev_sparse_list(cell_idx) %% %(size_a)s;
                       int %(pos_b)s = prev_sparse_list(cell_idx) / %(size_b)s;""" %
                           dict(pos_a = self.position_names[0],
                                pos_b = self.position_names[1],
                                size_a = self.code.acc.size_names[0],
                                size_b = self.code.acc.size_names[1]))

        # FIXME use proper position names here
        if len(self.position_names) == 1:
            self.code.add_code("loop_end",
                    """if(was_active) {
                               %s
                       }""" % ("\n".join([
                           """
                           {int idx = %(wrap_x)s;
                           if(!sparse_mask(idx)) {
                               sparse_list(sparse_cell_write_idx) = idx;
                               sparse_mask(idx) = true;
                               sparse_cell_write_idx++;
                           }}""" % dict(offs_x=offs[0],
                                        wrap_x=self.code.border.correct_position_c(["loop_x + %s" % (offs[0])])[0])
                               for offs in self.code.neigh.offsets])))
        elif len(self.position_names) == 2:
            self.code.add_code("loop_end",
                    """if(was_active) {
                               %s
                       }""" % ("\n".join([
                           """
                           {int px = loop_x + %(offs_x)s;
                           int py = loop_y + %(offs_y)s;
                           %(wrap)s;
                           int idx = px * %(size_x)s + py;
                           if(!sparse_mask(idx)) {
                               sparse_list(sparse_cell_write_idx) = idx;
                               sparse_mask(idx) = true;
                               sparse_cell_write_idx++;
                           }}""" % dict(offs_x=offs[0], offs_y=offs[1],
                                        size_x=self.code.acc.size_names[0],
                                        wrap="px = " + ("; py = ".join(self.code.border.correct_position_c(
                                            ("px", "py")
                                            ))))
                               for offs in self.code.neigh.offsets])))
        self.code.add_code("loop_end",
                """
                }
                // null the sparse mask
                sparse_mask = 0;
                sparse_list(sparse_cell_write_idx) = -1;
                """)

class OneDimSparseCellLoop(SparseCellLoop):
    requires_features = [one_dimension, activity]
    def __init__(self):
        self.position_names = "loop_x",

class TwoDimSparseCellLoop(SparseCellLoop):
    requires_features = [two_dimensions, activity]
    def __init__(self):
        self.position_names = "loop_x", "loop_y"

class OneDimSparseNondetCellLoop(OneDimSparseCellLoop):
    requires_features = [one_dimension, activity, random_generator]
    def __init__(self, probab=0.5):
        super(OneDimSparseNondetCellLoop, self).__init__()
        self.probab = probab

class TwoDimSparseNondetCellLoop(SparseCellLoop):
    requires_features = [two_dimensions, activity, random_generator]
    def __init__(self, probab=0.5):
        super(OneDimSparseNondetCellLoop, self).__init__()
        self.probab = probab
