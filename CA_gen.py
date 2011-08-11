""" This module tests slimming down the specification of cellular automaton
step functions by using re-usable components.

Ideally, only the very core of the computation would have to be written
once in C++ and once in python. The rest would then be done by the
composite classes.

Currently, the step function will only be generated as c++ code, but later,
the step function will be runnable as pure python code as well.

The parts the step function is decomposed into are:

  - A StateAccessor

    is responsible for writing to and reading from the configuration as
    well as knowing what shape and size the configuration has.

  - A CellLoop

    defines the order in which to loop over the configuration cells.

  - A BorderHandler

    handles the borders of the configuration by copying over parts or writing
    data. Maybe, in the future, it could also resize configurations on demand.

When these classes gain the capability to "generate" pure python code,
the inlining capabilities of the PyPy JIT will compensate the amount of
functions that take part in doing everything.
"""

from scipy import weave

class WeaveStepFuncVisitor(object):
    def __init__(self):
        self.code = None
        self.target = None

    def bind(self, code):
        """bind the visitor to a StepFunc"""
        assert self.code is None, "%r is already bound to %r" % (self, self.code)
        self.code = code

    def set_target(self, target):
        """target a CA instance"""
        assert self.target is None, "%r already targets %r" % (self, self.target)
        self.target = target

    def visit(self):
        """add code snippets to the code object."""
        pass

    def init_once(self):
        """initialize data on the target.

        this is pure python code that runs on init."""
        pass

    def new_config(self):
        """check and sanitize a new config.

        this is pure python code that runs when a new config is loaded."""
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

    def write_to(self, pos, value):
        """directly write to the next config at pos."""

    def write_to_current(self, pos, value):
        """directly write to the current config at pos."""

    def read_from(self, pos):
        """directly read from the current config at pos."""
        return 0

    def read_from_next(self, pos):
        """directly read from the next config at pos."""
        return 0

    def get_size(self, dimension=0):
        """generate a code bit to get the size of the config space in
        the specified dimension"""
        return "size"

    def get_size_of(self, dimension=0):
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
    """The WeaveStepFunc will compose different parts into a functioning
    step function."""
    def __init__(self, loop, accessor, neighbourhood, extra_code=[], target=None):
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

        self.visitors = [self.acc, self.neigh, self.loop] + extra_code

        for code in self.visitors:
            code.bind(self)

        self.target = target
        if self.target is not None:
            for code in self.visitors:
                code.set_target(self.target)

        for code in self.visitors:
            code.visit()

    def set_target(self, target):
        assert self.target is None, "%r already targets %r" % (self, self.target)
        self.target = target

    def add_code(self, hook, code):
        self.code[hook].append(code)

    def regen_code(self):
        code_bits = []
        for section in self.sections:
            code_bits.extend(self.code[section])
        self.code_text = "\n".join(code_bits)

    def inline(self):
        weave.inline( self.code_text,
            local_dict=dict((k, getattr(self.target, k)) for k in self.attrs))

    def new_conf(self):
        for code in self.visitors:
            code.new_conf(self.target)

    def init_once(self):
        for code in self.visitors:
            code.init_once()

class LinearStateAccessor(StateAccessor):
    def read_access(self, pos):
        return "cconf(%s, 0)" % pos

    def write_access(self, pos):
        return "nconf(%s, 0)" % pos

    def visit(self):
        self.code.add_code("localvars",
                """int result;""")
        self.code.add_code("post_compute",
                self.write_access(self.code.loop.get_position()) + " = result;")

    def read_from(self, pos):
        return self.target.currConf[pos]

    def write_to(self, pos, value):
        self.target.nextConf[pos] = value

    def write_to_current(self, pos, value):
        self.target.currConf[pos] = value

class LinearCellLoop(CellLoop):
    def get_position(self, offset=0):
        if offset == 0:
            return "i"
        else:
            return "i + %d" % (offset)

    def visit(self):
        self.code.add_code("loop_begin",
                """for(int i=1; i < sizeX-1; i++) {""")
        self.code.add_code("loop_end",
                """}""")

class LinearNeighbourhood(Neighbourhood):
    def __init__(self, names, offsets):
        super(Neighbourhood, self).__init__()
        self.names = tuple(names)
        self.offsets = tuple(offsets)
        assert len(self.names) == len(self.offsets)

    def visit(self):
        for name, offset in zip(self.names, self.offsets):
            self.code.add_code("pre_compute",
                "%s = %s;" % (name,
                             self.code.acc.read_access(self.code.loop.get_position(offset))))
        self.code.add_code("localvars",
                "int " + ", ".join(self.names) + ";")

    def neighbourhood_cells(self):
        return self.names

    def bounding_box(self, steps=1):
        return min(self.offsets), max(self.offsets)

class LinearBorderCopier(BorderHandler):
    def visit(self):
        self.code.add_code("after_step",
                self.code.acc.write_access("0") + " = " + self.code.acc.write_access("sizeX - 2") + ";\n" +
                self.code.acc.write_access("sizeX - 1") + " = " + self.code.acc.write_access("1") + ";")

    def new_config(self):
        left = self.code.acc.read_from(self.target, 1)
        right = self.code.acc.read_from(self.target, self.code.acc.get_size_of(self.target, 0) - 1)

        self.code.acc.write_to(self.target, 0, right)
        self.code.acc.write_to(self.target, self.code.acc.get_size_of(self.target, 0) - 2, left)

def test():
    binRuleTestCode = WeaveStepFunc(
            loop=LinearCellLoop(),
            accessor=LinearStateAccessor(),
            neighbourhood=LinearNeighbourhood(["l", "m", "r"], (-1, 0, 1)),
            extra_code=[LinearBorderCopier()])
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
