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

# TODO get some code in place that compares the run functions against the
#      official implementation.

# TODO separate the functions to make C code from the ones that do pure python
#      computation

# TODO instead of putting together lambdas, generate python code as strings
#      and compare performance in pypy

# TODO figure out how the code should handle resizing of configurations and
#      other such things.

import numpy as np
try:
    from scipy import weave
    from scipy.weave import converters
    USE_WEAVE=True
except ImportError:
    USE_WEAVE=False
    print "not using weave"

import random
import sys

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

    def init_once(self):
        """initialize data on the target.

        this is pure python code that runs on init."""

    def new_config(self):
        """check and sanitize a new config.

        this is pure python code that runs when a new config is loaded.
        it only changes the current configuration "cconf" of the automaton.
        after all new_config hooks have been run, they are multiplied."""

class StateAccessor(WeaveStepFuncVisitor):
    """A StateAccessor will supply read and write access to the state array.

    it also knows things about how the config space is shaped and sized and
    how to handle swapping or history of configs."""

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

    def multiplicate_config(self):
        """take the current config "cconf" and multiply it over all
        history slots that need to have duplicates at the beginning"""

    def swap_configs(self):
        """swap out all configs"""

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

            (minX, maxX,
             [minY, maxY,
              [minZ, maxZ]])"""
        return (-steps, steps)

class BorderHandler(WeaveStepFuncVisitor):
    """The BorderHandler is responsible for treating the borders of the
    configuration. One example is copying the leftmost border to the rightmost
    border and vice versa or ensuring the border cells are always 0."""

class BorderSizeEnsurer(BorderHandler):
    def new_config(self):
        # XXX all of this needs to be extended for multi-dim arrays
        super(BorderSizeEnsurer, self).new_config()
        bbox = self.code.neigh.bounding_box()
        # FIXME if the bbox goes into the positive values, abs is wrong. use the 
        # FIXME correct amount of minus signs instead?
        new_conf = np.zeros(len(self.target.cconf) + abs(bbox[0]) + abs(bbox[1]))
        new_conf[abs(bbox[0]):-abs(bbox[1])] = self.target.cconf
        self.target.cconf = new_conf

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
        """set the target of the step function. the target contains,
        among other things, the configurations."""
        assert self.target is None, "%r already targets %r" % (self, self.target)
        self.target = target
        for visitor in self.visitors:
            visitor.set_target(target)
        self.init_once()
        self.new_config()

    def add_code(self, hook, code):
        """add a snippet of C code to the section "hook"."""
        self.code[hook].append(code)

    def add_py_hook(self, hook, function):
        """add a python callable to the section "hook"."""
        self.pycode[hook].append(function)

    def regen_code(self):
        """regenerate the C and python code from the bits"""
        code_bits = []
        for section in self.sections:
            code_bits.extend(self.code[section])
        self.code_text = "\n".join(code_bits)

        self.visitors = tuple(self.visitors)
        self.pycode = dict((k, tuple(v)) for k, v in self.pycode.iteritems())

    def step_inline(self):
        """run a step of the simulator using weave.inline and the C code."""
        local_dict=dict((k, getattr(self.target, k)) for k in self.attrs)
        local_dict.update(self.consts)
        attrs = self.attrs + self.consts.keys()
        weave.inline( self.code_text, global_dict=local_dict, arg_names=attrs,
                      type_converters = converters.blitz)
        self.acc.swap_configs()

    def step_pure_py(self):
        """run a step of the simulator using the python callables hooked into
        the step function"""
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
            state["pos"] = pos
            state.update(self.neigh.get_neighbourhood(pos))
            runhooks("pre_compute")
            runhooks("compute")
            runhooks("post_compute")
        runhooks("after_step")
        self.acc.swap_configs()

    def new_config(self):
        """handle setting up and sanitising a newly set configuration in the
        target object."""
        for code in self.visitors:
            code.new_config()
        self.acc.multiplicate_config()

    def init_once(self):
        """initialise all the visitors after a configuration has been set."""
        for code in self.visitors:
            code.init_once()

class LinearStateAccessor(StateAccessor):
    def __init__(self, size):
        super(LinearStateAccessor, self).__init__()
        self.size = size

    def read_access(self, pos, skip_border=False):
        if skip_border:
            return "cconf(%s, 0)" % (pos)
        return "cconf(%s + %s, 0)" % (pos, self.border_l_name)

    def write_access(self, pos, skip_border=False):
        if skip_border:
            return "nconf(%s, 0)" % (pos)
        return "nconf(%s + %s, 0)" % (pos, self.border_l_name)

    def init_once(self):
        self.code.consts["sizeX"] = self.size
        self.code.attrs.extend(["nconf", "cconf"])

    def bind(self, target):
        super(LinearStateAccessor, self).bind(target)
        self.border_l = abs(self.code.neigh.bounding_box()[0])
        self.border_l_name = "BORDER_OFFSET"

    def visit(self):
        self.code.add_code("headers",
                "#define %s %d" % (self.border_l_name, self.border_l))
        self.code.add_code("localvars",
                """int result;""")
        self.code.add_code("post_compute",
                self.write_access(self.code.loop.get_pos()) + " = result;")

        self.code.add_py_hook("init",
                lambda state: dict(result=None))
        self.code.add_py_hook("post_compute",
                lambda state, code=self.code: code.acc.write_to(state["pos"], state["result"]))

    def read_from(self, pos, skip_border=False):
        if skip_border:
            return self.target.cconf[pos]
        return self.target.cconf[pos + self.border_l]

    def read_from_next(self, pos, skip_border=False):
        if skip_border:
            return self.target.nconf[pos]
        return self.target.nconf[pos + self.border_l]

    def write_to(self, pos, value, skip_border=False):
        if skip_border:
            self.target.nconf[pos] = value
        else:
            self.target.nconf[pos + self.border_l] = value

    def write_to_current(self, pos, value, skip_border=False):
        if skip_border:
            self.target.cconf[pos] = value
        else:
            self.target.cconf[pos + self.border_l] = value

    def get_size_of(self, dimension=0):
        return self.size

    def swap_configs(self):
        self.target.nconf, self.target.cconf = \
                self.target.cconf, self.target.nconf

    def multiplicate_config(self):
        self.target.nconf = self.target.cconf.copy()

class LinearCellLoop(CellLoop):
    def get_pos(self, offset=0):
        if offset == 0:
            return "i"
        else:
            return "i + %d" % (offset)

    def visit(self):
        self.code.add_code("loop_begin",
                """for(int i=0; i < sizeX; i++) {""")
        self.code.add_code("loop_end",
                """}""")

    def get_iter(self):
        return range(0, self.code.acc.get_size_of())

class LinearNondeterministicCellLoop(LinearCellLoop):
    def __init__(self, probab=0.5, random_generator=None, **kwargs):
        super(LinearNondeterministicCellLoop, self).__init__(**kwargs)
        if random_generator is None:
            self.random = random.Random()
        else:
            self.random = random_generator
        self.probab = probab

    def get_iter(self):
        def generator():
            for i in range(self.code.acc.get_size_of()):
                if self.random.random() < self.probab:
                    yield i
        return iter(generator())

    def visit(self):
        super(LinearNondeterministicCellLoop, self).visit()
        self.code.add_code("loop_begin",
                """if(rand() >= RAND_MAX * %s) continue;""" % (self.probab))
        self.code.add_code("localvars",
                """srand(randseed(0));""")
        self.code.add_code("after_step",
                """randseed(0) = rand();""")
        self.code.attrs.append("randseed")

    def set_target(self, target):
        super(LinearNondeterministicCellLoop, self).set_target(target)
        # FIXME how do i get the randseed out without using np.array?
        target.randseed = np.array([self.random.random()])

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

class LinearBorderCopier(BorderSizeEnsurer):
    def visit(self):
        # copying works like this:
        #
        # conf: [e][f] [a][b][c][d][e][f] [a][b]
        #       |----> |---------------->
        #       offset    sizeX           |---->
        #        l_b                        r_b
        # conf(i) <- conf(i + sizeX)
        # conf(offset + sizeX + i) <- conf(offset + i)

        bbox = self.code.neigh.bounding_box()
        left_border = abs(bbox[0])
        right_border = abs(bbox[1])
        copy_code = []
        for i in range(left_border):
            copy_code.append("%s = %s;" % (
                self.code.acc.write_access(i, skip_border=True),
                self.code.acc.write_access("sizeX + %d" % (i), skip_border=True)))

            self.code.add_py_hook("after_step",
                    lambda state: self.code.acc.write_to(i, skip_border=True,
                            value = self.code.acc.read_from_next(self.code.acc.get_size_of(0) + i, skip_border=True)))


        for i in range(right_border):
            copy_code.append("%s = %s;" % (
                self.code.acc.write_access("sizeX + " + str(i)),
                self.code.acc.write_access(str(i))))

            self.code.add_py_hook("after_step",
                    lambda state: self.code.acc.write_to(self.code.acc.get_size_of(0) + i,
                            value = self.code.acc.read_from_next(i)))

        self.code.add_code("after_step",
                "\n".join(copy_code))

    def new_config(self):
        super(LinearBorderCopier, self).new_config()

        bbox = self.code.neigh.bounding_box()
        left_border = abs(bbox[0])
        right_border = abs(bbox[1])
        for i in range(left_border):
            self.code.acc.write_to_current(i, skip_border=True,
                    value=self.code.acc.read_from(self.code.acc.get_size_of(0) + i, skip_border=True))
        for i in range(right_border):
            self.code.acc.write_to_current(self.code.acc.get_size_of(0) + i,
                    value=self.code.acc.read_from(i))

def test():
    cell_shadow, cell_full = "%#"
    back_shadow, back_full = ", "
    def build_array_pretty_printer(sizex, border_left, border_right, extra_left=0, extra_right=0):
        def pretty_print_array(arr):
            for cell in arr[border_left + sizex - extra_left - border_left:border_left + sizex]:
                sys.stdout.write(cell_shadow if cell > 0.5 else back_shadow)
            for cell in arr[border_left:border_left + sizex]:
                sys.stdout.write(cell_full if cell > 0.5 else back_full)
            for cell in arr[border_left:border_left + border_right + extra_right]:
                sys.stdout.write(cell_shadow if cell > 0.5 else back_shadow)
            sys.stdout.write("\n")
        return pretty_print_array

    class TestTarget(object):
        def __init__(self, size):
            rand = random.Random(11)
            self.size = size
            self.cconf = np.zeros(size)
            for i in range(size):
                self.cconf[i] = rand.choice([0, 1])
            self.nconf = self.cconf.copy()
            self.rule = np.array([0, 1, 1, 1, 1, 1, 1, 0])

    size = 75

    binRuleTestCode = WeaveStepFunc(
            #loop=LinearNondeterministicCellLoop(random_generator=random.Random(11)),
            loop=LinearCellLoop(),
            accessor=LinearStateAccessor(size=size),
            neighbourhood=LinearNeighbourhood(list("lmr"), (-1, 0, 1)),
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

    target = TestTarget(size)
    binRuleTestCode.set_target(target)
    binRuleTestCode.regen_code()

    b_l, b_r = binRuleTestCode.neigh.bounding_box()
    pretty_print_array = build_array_pretty_printer(size, abs(b_l), abs(b_r), 20, 20)

    print binRuleTestCode.code_text
    if USE_WEAVE:
        print "weave"
        for i in range(10000):
            binRuleTestCode.step_inline()
            pretty_print_array(target.cconf)
    else:
        print "pure"
        for i in range(10000):
            binRuleTestCode.step_pure_py()
            pretty_print_array(target.cconf)

if __name__ == "__main__":
    test()
