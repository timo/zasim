"""

"""
# This file is part of zasim. zasim is licensed under the BSD 3-clause license.
# See LICENSE.txt for details.

from .bases import StateAccessor
from .utils import gen_offset_pos, offset_pos

class SimpleStateAccessor(StateAccessor):
    """The SimpleStateAccessor offers a base for classes that just linearly
    grant access to any-dimensional configuration space."""

    size_names = ()
    """The names to use in the C code"""

    border_names = ((),)
    """The names of border offsets.

    The first tuple contains the borders with lower coordinate values, the
    second one contains the borders with higher coordinate values."""

    border_size = {}
    """The sizes of the borders.

    The key is the name of the border from border_names, the value is the size
    of the border."""

    size = None
    """The size of the target configuration."""

    cell_count = 0
    """The number of cells in the target configuration."""

    conf_names = ("nconf", "cconf")

    def set_size(self, size):
        super(SimpleStateAccessor, self).set_size(size)
        self.size = size
        self.cell_count = reduce(lambda a, b: a * b, self.size)
        if len(self.size) == 1:
            self.size_names = ("sizeX",)
            self.border_names = (("LEFT_BORDER",), ("RIGHT_BORDER",))
        elif len(self.size) == 2:
            self.size_names = ("sizeX", "sizeY")
            self.border_names = (("LEFT_BORDER", "UPPER_BORDER"), ("RIGHT_BORDER", "LOWER_BORDER"))
        else:
            raise NotImplementedError("SimpleStateAccessor only supports up to 2 dimensions.")

    def read_access(self, pos):
        return "cconf(%s)" % (", ".join(gen_offset_pos(pos, self.border_names[0])),)

    def write_access(self, pos):
        return "nconf(%s)" % (",".join(gen_offset_pos(pos, self.border_names[0])),)

    def init_once(self):
        """Set the sizeX const and register nconf and cconf for extraction
        from the targen when running C code."""
        super(SimpleStateAccessor, self).init_once()
        for sizename, size in zip(self.size_names, self.size):
            self.code.consts[sizename] = size
        self.code.consts["cell_count"] = self.cell_count
        self.code.attrs.extend(self.conf_names)

    def bind(self, code):
        """Get the bounding box from the neighbourhood object,
        set consts for borders."""
        super(SimpleStateAccessor, self).bind(code)
        bb = self.code.neigh.bounding_box()
        mins = [abs(a[0]) for a in bb]
        maxs = [abs(a[1]) for a in bb]
        self.border = (tuple(mins), tuple(maxs))
        for name, value in zip(sum(self.border_names, ()), sum(self.border, ())):
            self.code.consts[name] = value
            self.border_size[name] = value

    def visit(self):
        """Take care for result and sizeX to exist in python and C code,
        for the result to be written to the config space and for the configs
        to be swapped by the python code."""
        super(SimpleStateAccessor, self).visit()
        self.code.add_weave_code("localvars",
                """int result;""")
        self.code.add_weave_code("post_compute",
                self.write_access(self.code.loop.get_pos()) + " = result;")

        self.code.add_py_code("init",
                """result = None""")

        self.code.add_py_code("post_compute",
                """self.acc.write_to(pos, result)""")
        self.code.add_py_code("finalize",
                """self.acc.swap_configs()""")

    def set_target(self, target):
        """Get the size from the target objects config."""
        super(SimpleStateAccessor, self).set_target(target)
        if self.size is None:
            self.size = self.target.cconf.shape

    def read_from(self, pos):
        return self.target.cconf[offset_pos(pos, self.border[0])]

    def read_from_next(self, pos):
        return self.target.nconf[offset_pos(pos, self.border[0])]

    def write_to(self, pos, value):
        self.target.nconf[offset_pos(pos, self.border[0])] = value

    def write_to_current(self, pos, value):
        self.target.cconf[offset_pos(pos, self.border[0])] = value

    def get_size_of(self, dimension=0):
        return self.size[dimension]

    def swap_configs(self):
        """Swaps nconf and cconf in the target."""
        self.target.nconf, self.target.cconf = \
                self.target.cconf, self.target.nconf

    def multiplicate_config(self):
        """Copy cconf to nconf in the target."""
        self.target.nconf = self.target.cconf.copy()

    def gen_copy_code(self):
        """Generate a bit of C code to copy the current field over from the old
        config. This is necessary for instance for nondeterministic step funcs
        combined with swapping two confs around."""
        return "%s = %s;" % (self.write_access(self.code.loop.get_pos()),
                            self.read_access(self.code.loop.get_pos()))

    def gen_copy_py_code(self):
        """Generate a bit of py code to copy the current field over from the
        old config."""
        return "self.acc.write_to(pos, self.acc.read_from(pos))"

class SubcellAccessor(SimpleStateAccessor):
    """With the SubcellAccessor you can handle configurations where each cell
    is conceptually made up of multiple cells. This can be done either with
    one `ndarray` per subcell or a suitable record `ndarray`, from which views
    for each subcell "plane" can be created."""

    def __init__(self, cells):
        """Pass a list of names for the cells argument"""
        super(SubcellAccessor, self).__init__()
        self.cells = cells
        print "making a subcell accessor with cells: ", self.cells
        cnames = []
        for c in cells:
            cnames.extend(("cconf_%s" % c, "nconf_%s" % c))
        self.conf_names = tuple(cnames)

    def visit(self):
        """Take care for result and sizeX to exist in python and C code,
        for the result to be written to the config space and for the configs
        to be swapped by the python code."""
        super(SimpleStateAccessor, self).visit()
        for cell in self.cells:
            self.code.add_weave_code("localvars",
                    """int result_%s;""" % cell)

            self.code.add_weave_code("post_compute",
                    self.write_access(self.code.loop.get_pos(), cell) + " = result_%s;" % cell)

            self.code.add_py_code("init",
                    """result_%s = None""" % cell)

            self.code.add_py_code("post_compute",
                    """self.acc.write_to(pos, result_%s, "%s")""" % (cell, cell))

        self.code.add_py_code("finalize",
                """self.acc.swap_configs()""")

    def read_access(self, pos, cell):
        return "cconf_%s(%s)" % (cell, ", ".join(gen_offset_pos(pos, self.border_names[0])),)

    def write_access(self, pos, cell):
        return "nconf_%s(%s)" % (cell, ",".join(gen_offset_pos(pos, self.border_names[0])),)

    def read_from(self, pos, cell):
        cconf = getattr(self.target, "cconf_%s" % cell)
        return cconf[offset_pos(pos, self.border[0])]

    def read_from_next(self, pos, cell):
        nconf = getattr(self.target, "nconf_%s" % cell)
        return nconf[offset_pos(pos, self.border[0])]

    def write_to(self, pos, value, cell):
        nconf = getattr(self.target, "nconf_%s" % cell)
        nconf[offset_pos(pos, self.border[0])] = value

    def write_to_current(self, pos, value, cell):
        cconf = getattr(self.target, "cconf_%s" % cell)
        cconf[offset_pos(pos, self.border[0])] = value

    def get_size_of(self, dimension=0):
        return self.size[dimension]

    def multiplicate_config(self):
        """Copy cconf to nconf in the target."""
        self.target.nconf = dict()
        for k in self.cells:
            cconf = getattr(self.target, "cconf_%s" % k)
            setattr(self.target, "nconf_%s" % k, cconf.copy())

    def swap_configs(self):
        for cell in self.cells:
            nconf = getattr(self.target, "nconf_%s" % cell)
            cconf = getattr(self.target, "cconf_%s" % cell)
            setattr(self.target, "nconf_%s" % cell, cconf)
            setattr(self.target, "cconf_%s" % cell, nconf)

    def gen_copy_code(self):
        """Generate a bit of C code to copy the current field over from the old
        config. This is necessary for instance for nondeterministic step funcs
        combined with swapping two confs around."""
        for cell in self.cells:
            return "%s = %s;" % (self.write_access(self.code.loop.get_pos(), cell),
                                self.read_access(self.code.loop.get_pos(), cell))

    def gen_copy_py_code(self):
        """Generate a bit of py code to copy the current field over from the
        old config."""
        res = []
        for cell in self.cells:
            res.append("self.acc.write_to(pos, self.acc.read_from(pos, '%s'), '%s')" % (cell, cell))
        return "\n".join(res)
