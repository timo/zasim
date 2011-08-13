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

# TODO decide between letting the cells be calibrated by the accessor or
#      having loop and border cooperate so that no accesses beyond the
#      border are possible

# TODO get some code in place that compares the run functions against the
#      official implementation.

# TODO separate the functions to make C code from the ones that do pure python
#      computation

# TODO instead of putting together lambdas, generate python code as strings
#      and compare performance in pypy

import numpy as np
try:
    from scipy import weave
    from scipy.weave import converters
    USE_WEAVE=True
except:
    USE_WEAVE=False

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

    def get_pos_of(self, offset):
        """returns the current position plus the offset in python."""
        return offset

    def get_iter(self):
        """returns an iterator for iterating over the config space in python"""
        return iter([])

class Neighbourhood(WeaveStepFuncVisitor):
    """A Neighbourhood is responsible for getting states from neighbouring cells."""

    def neighbourhood_cells(self):
        """Get the names of the neighbouring cells."""

    def get_neighbourhood(self, pos):
        """Get the values of the neighbouring cells for pos in python"""
        return {}

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

        # those are for generated c code
        self.sections = "headers localvars loop_begin pre_compute compute post_compute loop_end after_step".split()
        self.code = dict((s, []) for s in self.sections)
        self.code_text = ""

        # those are for composed python functions
        self.pysections = "init pre_compute compute post_compute after_step".split()
        self.pycode = dict((s, []) for s in self.pysections)

        self.attrs = []
        self.consts = {}

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
        for visitor in self.visitors:
            visitor.set_target(target)
        self.init_once()
        self.new_config()

    def add_code(self, hook, code):
        self.code[hook].append(code)

    def add_py_hook(self, hook, function):
        self.pycode[hook].append(function)

    def regen_code(self):
        code_bits = []
        for section in self.sections:
            code_bits.extend(self.code[section])
        self.code_text = "\n".join(code_bits)

        self.visitors = tuple(self.visitors)
        self.pycode = dict((k, tuple(v)) for k, v in self.pycode.iteritems())

    def step_inline(self):
        local_dict=dict((k, getattr(self.target, k)) for k in self.attrs)
        local_dict.update(self.consts)
        attrs = self.attrs + self.consts.keys()
        weave.inline( self.code_text, global_dict=local_dict, arg_names=attrs,
                      type_converters = converters.blitz)
        self.target.nconf, self.target.cconf = self.target.cconf, self.target.nconf

    def step_pure_py(self):
        state = self.consts.copy()
        state.update(dict((k, getattr(self.target, k)) for k in self.attrs))
        def runhooks(hook):
            for hook in self.pycode[hook]:
                upd = hook(state)
                if isinstance(upd, dict):
                    state.update(upd)

        runhooks("init")
        loop_iter = self.loop.get_iter()
        for pos in loop_iter:
            state.update(dict(pos=pos))
            state.update(self.neigh.get_neighbourhood(pos))
            runhooks("pre_compute")
            runhooks("compute")
            runhooks("post_compute")
        runhooks("after_step")
        self.target.nconf, self.target.cconf = self.target.cconf, self.target.nconf

    def new_config(self):
        for code in self.visitors:
            code.new_config()

    def init_once(self):
        for code in self.visitors:
            code.init_once()

class LinearStateAccessor(StateAccessor):
    def __init__(self, size):
        super(LinearStateAccessor, self).__init__()
        self.size = size

    def read_access(self, pos):
        return "cconf(%s, 0)" % pos

    def write_access(self, pos):
        return "nconf(%s, 0)" % pos

    def init_once(self):
        self.code.consts["sizeX"] = self.size
        self.code.attrs.extend(["nconf", "cconf"])

    def visit(self):
        self.code.add_code("localvars",
                """int result;""")
        self.code.add_code("post_compute",
                self.write_access(self.code.loop.get_pos()) + " = result;")

        self.code.add_py_hook("init",
                lambda state: dict(result=None))
        self.code.add_py_hook("post_compute",
                lambda state, code=self.code: code.acc.write_to(state["pos"], state["result"]))

    def read_from(self, pos):
        return self.target.cconf[pos]

    def read_from_next(self, pos):
        return self.target.nconf[pos]

    def write_to(self, pos, value):
        self.target.nconf[pos] = value

    def write_to_current(self, pos, value):
        self.target.cconf[pos] = value

    def get_size_of(self, dimension=0):
        return self.size

class LinearCellLoop(CellLoop):
    def get_pos(self, offset=0):
        if offset == 0:
            return "i"
        else:
            return "i + %d" % (offset)

    def visit(self):
        self.code.add_code("loop_begin",
                """for(int i=1; i < sizeX-1; i++) {""")
        self.code.add_code("loop_end",
                """}""")

    def get_iter(self):
        return range(1, self.code.acc.get_size_of() - 1)

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
                             self.code.acc.read_access(self.code.loop.get_pos(offset))))
        self.code.add_code("localvars",
                "int " + ", ".join(self.names) + ";")

        self.code.add_py_hook("pre_compute",
                lambda state, code=self.code: dict(zip(self.names,
                    [self.code.acc.read_from(state["pos"] + offset)
                        for offset in self.offsets])))

    def neighbourhood_cells(self):
        return self.names

    def bounding_box(self, steps=1):
        return min(self.offsets), max(self.offsets)

class LinearBorderCopier(BorderHandler):
    def visit(self):
        # XXX this still has to take the neighbourhood bounding box into account
        self.code.add_code("after_step",
                self.code.acc.write_access("0") + " = " + self.code.acc.write_access("sizeX - 2") + ";\n" +
                self.code.acc.write_access("sizeX - 1") + " = " + self.code.acc.write_access("1") + ";")

        self.code.add_py_hook("after_step",
                lambda state: self.code.acc.write_to_current(0, self.code.acc.read_from(self.code.acc.get_size_of(0) - 2)) and
                              self.code.acc.write_to_current(self.code.acc.get_size_of(0) - 1, self.code.acc.read_from(1)))

    def new_config(self):
        left = self.code.acc.read_from(1)
        right = self.code.acc.read_from(self.code.acc.get_size_of(0) - 1)

        self.code.acc.write_to(0, right)
        self.code.acc.write_to(self.code.acc.get_size_of(0) - 2, left)

def test():
    import random
    class TestTarget(object):
        def __init__(self, size):
            self.size = size
            self.cconf = np.zeros(size)
            for i in range(size):
                self.cconf[i] = random.choice([0, 1])
            self.nconf = self.cconf.copy()
            self.rule = np.array([0, 0, 1, 0, 1, 1, 0, 1])

    binRuleTestCode = WeaveStepFunc(
            loop=LinearCellLoop(),
            accessor=LinearStateAccessor(size=1000),
            neighbourhood=LinearNeighbourhood(["l", "m", "r"], (-1, 0, 1)),
            extra_code=[LinearBorderCopier()])

    binRuleTestCode.attrs.append("rule")
    binRuleTestCode.add_code("localvars",
            """int state;""")
    binRuleTestCode.add_code("compute",
            """state =  l << 2;
  state += m << 1;
  state += r;
  result = rule(state);""")

    binRuleTestCode.add_py_hook("compute",
            lambda state: dict(result=state["rule"][int(state["l"] * 4 + state["m"] * 2 + state["r"])]))

    target = TestTarget(1000)
    binRuleTestCode.set_target(target)
    binRuleTestCode.regen_code()
    print binRuleTestCode.code_text
    if USE_WEAVE:
        print "weave"
        for i in range(10000):
            binRuleTestCode.step_inline()
    else:
        print "pure"
        for i in range(1000):
            binRuleTestCode.step_pure_py()

if __name__ == "__main__":
    test()
