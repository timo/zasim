"""This module offers the ability to slim down the specification of
cellular automaton step functions using re-usable components.

You only need to write the core computation once in C and once in python,
the rest will be done for you by the components offered in this module.

The parts the step function is decomposed into are all subclasses of
:class:`WeaveStepFuncVisitor`. The base classes available are:

  - A :class:`StateAccessor`

    is responsible for writing to and reading from the configuration as
    well as knowing what shape and size the configuration has.

  - A :class:`CellLoop`

    defines the order in which to loop over the configuration cells.

  - A :class:`Neighbourhood`

    is responsible for getting the relevant fields for each local step.

  - A :class:`BorderHandler`

    handles the borders of the configuration by copying over parts or writing
    data. Maybe, in the future, it could also resize configurations on demand.


All of those classes are used to initialise a :class:`WeaveStepFunc` object,
which can then target a configuration object with the method 
:meth:`~WeaveStepFunc.set_target`.

"""

# TODO separate the functions to make C code from the ones that do pure python
#      computation

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

from random import Random
import sys
import new

class WeaveStepFunc(object):
    """The WeaveStepFunc composes different parts into a functioning
    step function."""
    def __init__(self, loop, accessor, neighbourhood, extra_code=[], target=None, **kwargs):
        """The Constructor creates a weave-based step function from the specified parts.

        loop          -  a :class:`CellLoop`, that adds a loop at loop_begin
                         and loop_end.
        accessor      -  a :class:`StateAccessor`, that handles accesses to the state
                         array as well as setting the cell value during
                         the loop.
        neighbourhood -  a :class:`Neighbourhood`, that fetches neighbouring
                         cell values into known variables.
        extra_code    -  further :class:`WeaveStepFuncVisitor`, that add more
                         behaviour. Usually at least a :class:`BorderCopier`."""

        super(WeaveStepFunc, self).__init__(**kwargs)

        # those are for generated c code
        self.sections = "headers localvars loop_begin pre_compute compute post_compute loop_end after_step".split()
        self.code = dict((s, []) for s in self.sections)
        self.code_text = ""

        # those are for composed python functions
        self.pysections = "init pre_compute compute post_compute after_step finalize".split()
        self.pycode = dict((s, []) for s in self.pysections)
        self.pycode_indent = dict((s, 4) for s in self.pysections)
        for section in "pre_compute compute post_compute".split():
            self.pycode_indent[section] = 8

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
        """add a string of python code to the section "hook"."""
        assert isinstance(function, basestring), "py hooks must be strings now."
        function = function.split("\n")
        newfunc = []

        for line in function:
            newfunc.append(" " * self.pycode_indent[hook] + line)

        self.pycode[hook].append("\n".join(newfunc))

    def gen_code(self):
        """regenerate the C and python code from the bits"""
        # freeze visitors and code bits
        self.visitors = tuple(self.visitors)
        for hook in self.code.keys():
            self.code[hook] = tuple(self.code[hook])

        code_bits = []
        for section in self.sections:
            code_bits.extend(self.code[section])
        self.code_text = "\n".join(code_bits)

        # freeze python code bits
        for hook in self.pycode.keys():
            self.pycode[hook] = tuple(self.pycode[hook])

        code_bits = ["""def step_pure_py(self):"""]
        def append_code(section):
            code_bits.append("# from hook %s" % section)
            code_bits.append("\n".join(self.pycode[section]))

        append_code("init")
        code_bits.append("    for pos in self.loop.get_iter():")
        append_code("pre_compute")
        append_code("compute")
        append_code("post_compute")
        append_code("after_step")
        append_code("finalize")
        code_bits.append("")
        code_text = "\n".join(code_bits)
        code_object = compile(code_text, "<string>", "exec")
        print code_text

        myglob = globals()
        myloc = locals()
        exec code_object in myglob, myloc
        self.step_pure_py = new.instancemethod(myloc["step_pure_py"], self, self.__class__)

    def step_inline(self):
        """run a step of the simulator using weave.inline and the C code."""
        local_dict=dict((k, getattr(self.target, k)) for k in self.attrs)
        local_dict.update(self.consts)
        attrs = self.attrs + self.consts.keys()
        weave.inline( self.code_text, global_dict=local_dict, arg_names=attrs,
                      type_converters = converters.blitz)
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

    def write_access(self, pos):
        """generate a code bit to write to the new config at pos.

        example: nconf(pos, 0)"""

    def write_to(self, pos, value):
        """directly write to the next config at pos."""

    def write_to_current(self, pos, value):
        """directly write to the current config at pos."""

    def read_from(self, pos):
        """directly read from the current config at pos."""

    def read_from_next(self, pos):
        """directly read from the next config at pos."""

    def get_size(self, dimension=0):
        """generate a code bit to get the size of the config space in
        the specified dimension"""

    def get_size_of(self, dimension=0):
        """get the size of the config space in the specified dimension."""

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

    def get_pos_of(self, offset):
        """returns the current position plus the offset in python."""

    def get_iter(self):
        """returns an iterator for iterating over the config space in python"""

class Neighbourhood(WeaveStepFuncVisitor):
    """A Neighbourhood is responsible for getting states from neighbouring cells."""

    def neighbourhood_cells(self):
        """Get the names of the neighbouring cells."""

    def get_neighbourhood(self, pos):
        """Get the values of the neighbouring cells for pos in python"""

    def bounding_box(self, steps=1):
        """Find out, how many cells, at most, have to be read after
        a number of steps have been done.

        It will return a tuple with relative values where 0 is the index of the
        current cell. It will have a format like:

            (minX, maxX,
             [minY, maxY,
              [minZ, maxZ]])"""

class BorderHandler(WeaveStepFuncVisitor):
    """The BorderHandler is responsible for treating the borders of the
    configuration. One example is copying the leftmost border to the rightmost
    border and vice versa or ensuring the border cells are always 0."""

class BorderSizeEnsurer(BorderHandler):
    def new_config(self):
        # TODO all of this needs to be extended for multi-dim arrays
        super(BorderSizeEnsurer, self).new_config()
        bbox = self.code.neigh.bounding_box()
        # FIXME if the bbox goes into the positive values, abs is wrong. use the 
        # FIXME correct amount of minus signs instead?
        new_conf = np.zeros(len(self.target.cconf) + abs(bbox[0]) + abs(bbox[1]))
        new_conf[abs(bbox[0]):-abs(bbox[1])] = self.target.cconf
        self.target.cconf = new_conf

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
                """result = None""")
        self.code.add_py_hook("init",
                """sizeX = %d""" % (self.code.acc.get_size_of(0)))
        self.code.add_py_hook("post_compute",
                """self.acc.write_to(pos, result)""")
        self.code.add_py_hook("finalize",
                """self.acc.swap_configs()""")

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
            self.random = Random()
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

        assignments = ["%s = self.acc.read_from(pos + %d)" % (
                name, offset) for name, offset in zip(self.names, self.offsets)]
        self.code.add_py_hook("pre_compute",
                "\n".join(assignments))

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
                    """self.acc.write_to(%d, skip_border=True,
    value=self.acc.read_from_next(%d, skip_border=True))""" % (i, self.code.acc.get_size_of(0) + i))


        for i in range(right_border):
            copy_code.append("%s = %s;" % (
                self.code.acc.write_access("sizeX + " + str(i)),
                self.code.acc.write_access(str(i))))

            self.code.add_py_hook("after_step",
                    """self.acc.write_to(%d,
    value=self.acc.read_from_next(%d))""" % (self.code.acc.get_size_of(0) + i, i))

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

class TestTarget(object):
    def __init__(self, size, rule=126, config=None, **kwargs):
        super(TestTarget, self).__init__(**kwargs)
        self.size = size
        if config is None:
            self.cconf = np.zeros(size)
            rand = Random(11)
            for i in range(size):
                self.cconf[i] = rand.choice([0, 1])
        else:
            self.cconf = config.copy()

        self.nconf = self.cconf.copy()
        self.rule = np.zeros( 8 )

        for i in range( 8 ):
            if ( rule & ( 1 << i ) ):
                self.rule[i] = 1

class BinRule(TestTarget):
    def __init__(self, size, deterministic=True, rule=126, config=None, **kwargs):
        super(BinRule, self).__init__(size, rule, config, **kwargs)
        self.stepfunc = WeaveStepFunc(
                loop=LinearCellLoop() if deterministic
                     else LinearNondeterministicCellLoop(),
                accessor=LinearStateAccessor(size=size),
                neighbourhood=LinearNeighbourhood(list("lmr"), (-1, 0, 1)),
                extra_code=[LinearBorderCopier()])

        self.stepfunc.attrs.append("rule")
        self.stepfunc.add_code("localvars",
                """int state;""")
        self.stepfunc.add_code("compute",
                """state =  l << 2;
      state += m << 1;
      state += r;
      result = rule(state);""")

        self.stepfunc.add_py_hook("compute",
                """result = self.target.rule[int(l * 4 + m * 2 + r)]""")

        self.stepfunc.set_target(self)
        self.stepfunc.gen_code()

    def step_inline(self):
        self.stepfunc.step_inline()

    def step_pure_py(self):
        self.stepfunc.step_pure_py()

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


    size = 75

    bin_rule = BinRule(size, rule=110)

    b_l, b_r = bin_rule.stepfunc.neigh.bounding_box()
    pretty_print_array = build_array_pretty_printer(size, abs(b_l), abs(b_r), 20, 20)

    print bin_rule.stepfunc.code_text
    if USE_WEAVE:
        print "weave"
        for i in range(10000):
            bin_rule.step_inline()
            pretty_print_array(bin_rule.cconf)
    else:
        print "pure"
        for i in range(10000):
            bin_rule.step_pure_py()
            pretty_print_array(bin_rule.cconf)

if __name__ == "__main__":
    if "pure" in sys.argv:
        USE_WEAVE = False
    test()
