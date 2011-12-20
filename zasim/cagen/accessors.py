"""

{LICENSE_TEXT}
"""
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
        self.code.attrs.extend(["nconf", "cconf"])

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
        self.code.add_code("localvars",
                """int result;""")
        self.code.add_code("post_compute",
                self.write_access(self.code.loop.get_pos()) + " = result;")

        self.code.add_py_hook("init",
                """result = None""")
        for sizename, value in zip(self.size_names, self.size):
            self.code.add_py_hook("init",
                    """%s = %d""" % (sizename, value))
        self.code.add_py_hook("post_compute",
                """self.acc.write_to(pos, result)""")
        self.code.add_py_hook("finalize",
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


