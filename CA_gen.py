"""This module tests slimming down the specification of cellular automaton
step functions by using re-usable components.

Currently, the step function will only be generated as c++ code, but later, the
step function will be runnable as pure python code as well.

The parts the step function is decomposed into are:

  - A StateAccessor

    is responsible for writing to and reading from the configuration as
    well as knowing what shape and size the configuration has.

  - A CellLoop

    defines the order in which to loop over the configuration cells.

  - A BorderHandler

    handles the borders of the configuration by copying over parts or writing
    data. Maybe, in the future, it could also resize configurations on demand.

When these classes gain the capability to "generate" pure python code, the
inlining capabilities of the PyPy JIT will compensate the amount of functions
that take part in doing everything.
"""

from scipy import weave

class WeaveStepFuncVisitor(object):
    def visit(self, code):
        """add code snippets to the code object."""
        pass

    def init_once(self, code, target):
        """initialize data on the target."""
        pass

    def new_config(self, code, target):
        """check and sanitize a new config."""
        pass

class StateAccessor(WeaveStepFuncVisitor):
    """A StateAccessor will supply read and write access to the state array.

    it also knows things about how the config space is shaped and sized."""

    def read_access(self, pos):
        """generate a code bit for reading from the old config at pos.

        example: cconf(pos, 0)"""
        return ""

    def write_access(self, pos):
        """generate a code bit to write to the new config at pos.

        example: nconf(pos, 0)"""
        return ""

    def write_to(self, target, pos, value):
        """directly write to the config supplied by target at pos."""

    def read_from(self, target, pos):
        """directly read from the config supplied by target at pos."""
        return 0

    def get_size(self, code, dimension=0):
        """generate a code bit to get the size of the config space in
        the specified dimension"""
        return "size"

    def get_size_of(self, target, dimension=0):
        """get the size of the config space in the specified dimension."""
        return 0

class CellLoop(WeaveStepFuncVisitor):
    """A CellLoop is responsible for looping over cell space and giving access
    to the current position."""
    def get_pos(self, offset):
        """returns a code bit to get the current position in config space"""
        return offset

class Neighbourhood(WeaveStepFuncVisitor):
    """A Neighbourhood is responsible for getting states from neighbouring cells."""

    def neighbourhood_cells(self):
        """Get the names of the neighbouring cells."""

    def bounding_box(self, steps=1):
        """Find out, how many cells, at most, have to be read after
        a number of steps have been done.

        It will return a tuple with relative values where 0 is the index of the
        current cell. It will have a format like:

            (minX, [minY, [minZ]],
             maxX, [maxY, [maxZ]])"""
        return (-steps, steps)

class BorderHandler(WeaveStepFuncVisitor):
    """The BorderHandler is responsible for treating the borders of the
    configuration. One example is copying the leftmost border to the rightmost
    border and vice versa or ensuring the border cells are always 0."""
    pass

class WeaveStepFunc(object):
    def __init__(self, loop, accessor, neighbourhood, extra_code=[]):
        """create a weave-based step function from the specified parts.

        loop          -  a CellLoop, that adds a loop at loop_begin
                         and loop_end.
        accessor      -  a StateAccessor, that handles accesses to the state
                         array as well as setting the cell value during
                         the loop.
        neighbourhood -  a Neighbourhood, that fetches neighbouring
                         cell values into known variables.
        extra_code    -  further WeaveStepFuncVisitors, that add more
                         behaviour."""
        self.sections = "headers localvars loop_begin pre_compute compute post_compute loop_end after_step".split()
        self.code = dict((s, []) for s in self.sections)
        self.code_text = ""

        self.attrs = []

        self.acc = accessor
        self.neigh = neighbourhood
        self.loop = loop

        self.acc.visit(self)
        self.neigh.visit(self)
        self.loop.visit(self)

        for code in extra_code:
            code.visit(self)

    def add_code(self, hook, code):
        self.code[hook].append(code)

    def regen_code(self):
        code_bits = []
        for section in self.sections:
            code_bits.extend(self.code[section])
        self.code_text = "\n".join(code_bits)

    def inline(self, target):
        weave.inline( self.code_text,
            local_dict=dict((k, getattr(target, k)) for k in self.attrs))

class LinearStateAccessor(StateAccessor):
    def read_access(self, pos):
        return "cconf(%s, 0)" % pos

    def write_access(self, pos):
        return "nconf(%s, 0)" % pos

    def visit(self, code):
        code.add_code("localvars",
                """int result;""")
        code.add_code("post_compute",
                self.write_access(code.loop.get_position()) + " = result")

    def read_from(self, target, pos):
        return target.currConf[pos]

    def write_to(self, target, pos, value):
        target.currConf[pos] = value

class LinearCellLoop(CellLoop):
    def get_position(self, offset=0):
        if offset != 0:
            return "i"
        else:
            return "i + %d" % (offset)

    def visit(self, code):
        code.add_code("loop_begin",
                """for(int i=1; i < sizeX-1; i++) {""")
        code.add_code("loop_end",
                """}""")

class LinearNeighbourhood(Neighbourhood):
    def __init__(self, names, offsets):
        self.names = tuple(names)
        self.offsets = tuple(offsets)
        assert len(self.names) == len(self.offsets)

    def visit(self, code):
        for name, offset in zip(self.names, self.offsets):
            code.add_code("pre_compute",
                "%s = %s" % (name,
                             code.acc.read_access(code.loop.get_position(offset))))

    def neighbourhood_cells(self):
        return self.names

    def bounding_box(self, steps=1):
        return min(self.offsets), max(self.offsets)

class LinearBorderCopier(BorderHandler):
    def visit(self, code):
        code.add_code("after_step",
                code.acc.write_access("0") + " = " + code.acc.write_access("sizeX - 2") + ";\n" +
                code.acc.write_access("sizeX - 1") + " = " + code.acc.write_access("1") + ";")

    def new_config(self, code, target):
        left = code.acc.read_from(target, 1)
        right = code.acc.read_from(target, code.acc.get_size_of(target, 0) - 1)

        code.acc.write_to(target, 0, right)
        code.acc.write_to(target, code.acc.get_size_of(target, 0) - 2, left)

def test():
    binRuleTestCode = WeaveStepFunc(
            loop=LinearCellLoop(),
            accessor=LinearStateAccessor(),
            neighbourhood=LinearNeighbourhood(["l", "m", "r"], (-1, 0, 1)))
    LinearBorderCopier().visit(binRuleTestCode)
    binRuleTestCode.attrs += "rule"
    binRuleTestCode.add_code("localvars",
            """int state;""")
    binRuleTestCode.add_code("compute",
            """state =  l << 2;
  state += m << 1;
  state += r;
  result = rule(state);""")
    binRuleTestCode.regen_code()
    print binRuleTestCode.code_text

if __name__ == "__main__":
    test()
