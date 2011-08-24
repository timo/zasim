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

  - A :class:`Computation`

    handles the computation that turns the data from the neighbourhood into
    the result that goes into the value for the next step.

All of those classes are used to initialise a :class:`WeaveStepFunc` object,
which can then target a configuration object with the method
:meth:`~WeaveStepFunc.set_target`.

.. testsetup:: *

    from zasim import cagen
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

try:
    from numpy import ndarray
    HAVE_MULTIDIM = True
except:
    print "multi-dimensional arrays are not available"
    HAVE_MULTIDIM = False

try:
    arr = np.array(range(10))
    foo = arr[(1,)]
    HAVE_TUPLE_ARRAY_INDEX = True
except TypeError:
    HAVE_TUPLE_ARRAY_INDEX = False
    import re
    TUPLE_ACCESS_FIX = re.compile(r"\((\d+),\)")
    def tuple_array_index_fixup(line):
        return TUPLE_ACCESS_FIX.sub(r"\1", line)

from random import Random
from itertools import product
import sys
import new

EXTREME_PURE_PY_DEBUG = False

if HAVE_TUPLE_ARRAY_INDEX:
    def offset_pos(pos, offset):
        """Offset a position by an offset. Any amount of dimensions should work."""
        return tuple([a + b for a, b in zip(pos, offset)])
else:
    def offset_pos(pos, offset):
        """Offset a position by an offset. Only works for 1d."""
        if isinstance(pos, tuple):
            pos = pos[0]
        if isinstance(offset, tuple):
            offset = offset[0]
        return pos + offset

def gen_offset_pos(pos, offset):
    """Generate code to offset a position by an offset.

    >>> cagen.gen_offset_pos(["i", "j"], ["foo", "bar"])
    ['i + foo', 'j + bar']"""
    return ["%s + %s" % (a, b) for a, b in zip(pos, offset)]

class WeaveStepFunc(object):
    """The WeaveStepFunc composes different parts into a functioning
    step function."""
    def __init__(self, loop, accessor, neighbourhood, extra_code=[],
                 target=None, **kwargs):
        """The Constructor creates a weave-based step function from the
        specified parts.

        :param loop: A :class:`CellLoop`, that adds a loop at loop_begin
                     and loop_end.
        :param accessor: A :class:`StateAccessor`, that handles accesses to the
                         state array as well as setting the cell value during
                         the loop.
        :param neighbourhood: A :class:`Neighbourhood`, that fetches
                              neighbouring cell values into known variables.
        :param extra_code: Further :class:`WeaveStepFuncVisitor` classes, that
                           add more behaviour. 
                           Usually at least a :class:`BorderCopier`."""

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

    def add_code(self, hook, code):
        """Add a snippet of C code to the section "hook".

        :param hook: the section to append the code to.
        :param code: the C source code to add."""
        self.code[hook].append(code)

    def add_py_hook(self, hook, function):
        """Add a string of python code to the section "hook".

        :param hook: the section to append the code to.
        :param function: the python code to add (as a string)."""
        assert isinstance(function, basestring), "py hooks must be strings now."
        function = function.split("\n")
        newfunc = []

        for line in function:
            if not HAVE_TUPLE_ARRAY_INDEX:
                line = tuple_array_index_fixup(line)
            newfunc.append(" " * self.pycode_indent[hook] + line)
            if EXTREME_PURE_PY_DEBUG:
                indent = len(line) - len(line.lstrip(" "))
                words = line.strip().split(" ")
                if len(words) > 1 and words[1] == "=":
                    newfunc.append(" " * (self.pycode_indent[hook] + indent) + "print " + words[0])

        self.pycode[hook].append("\n".join(newfunc))

    def gen_code(self):
        """Generate the C and python code from the bits.

        .. note::
            Once this function is run, no more visitors can be added."""
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

        myglob = globals()
        myloc = locals()
        exec code_object in myglob, myloc
        self.pure_py_code_text = code_text
        self.step_pure_py = new.instancemethod(myloc["step_pure_py"], self, self.__class__)

    def step_inline(self):
        """Run a step of the simulator using weave.inline and the generated
        C code."""
        local_dict=dict((k, getattr(self.target, k)) for k in self.attrs)
        local_dict.update(self.consts)
        attrs = self.attrs + self.consts.keys()
        weave.inline( self.code_text, global_dict=local_dict, arg_names=attrs,
                      type_converters = converters.blitz)
        self.acc.swap_configs()

    def step_pure_py(self):
        """Run a step using the compiled python code.

        .. note::
            This function will be generated by gen_code."""
        raise ValueError("Cannot run pure python step until gen_code has been"
                         "called")


    def set_target(self, target):
        """Set the target of the step function. The target contains,
        among other things, the configurations."""
        assert self.target is None, "%r already targets %r" % (self, self.target)
        self.target = target
        for visitor in self.visitors:
            visitor.set_target(target)
        self.init_once()
        self.new_config()

    def init_once(self):
        """Initialise all the visitors after a configuration has been set."""
        for code in self.visitors:
            code.init_once()

    def new_config(self):
        """Handle a changed config in the target.

        Call this after setting the targets cconf attribute to something new."""
        # TODO explode when the size has changed? or leave that to the accessor?
        for code in self.visitors:
            code.new_config()
        self.acc.multiplicate_config()

class WeaveStepFuncVisitor(object):
    """Base class for step function visitor objects."""
    def __init__(self):
        self.code = None
        self.target = None

    def bind(self, code):
        """Bind the visitor to a StepFunc.

        .. note::
            Once bonded, the visitor object will refuse to be rebound."""
        assert self.code is None, "%r is already bound to %r" % (self, self.code)
        self.code = code

    def set_target(self, target):
        """Target a CA instance

        .. note::
            Once a target has been set, the visitor object will refuse to retarget."""
        assert self.target is None, "%r already targets %r" % (self, self.target)
        self.target = target

    def visit(self):
        """Adds code to the bound step func.

        This will be called after bind, but not necessarily after set_target.

        .. note::
            Never call this function on your own.
            This method will be called by :meth:`WeaveStepFunc.__init__`."""

    def init_once(self):
        """Initialize data on the target.

        This function will be called when the :class:`WeaveStepFunc` has
        first had its target set."""

    def new_config(self):
        """Check and sanitize a new config.

        This is pure python code that runs when a new config is loaded.
        it only changes the current configuration "cconf" of the automaton.
        after all new_config hooks have been run, they are multiplied."""

class StateAccessor(WeaveStepFuncVisitor):
    """A StateAccessor will supply read and write access to the state array.

    It also knows things about how the config space is shaped and sized and
    how to handle swapping or history of configs.

    Additionally, it knows how far to offset reads and writes, so that cells at
    the lowest coordinates will have a border of data around them.

    Supplying skip_border=True to any read or write function will remove the
    border from the calculation. This is mainly useful for BorderHandler."""

    def read_access(self, pos, skip_border=False):
        """Generate a bit of C code for reading from the old config at pos."""

    def write_access(self, pos, skip_border=False):
        """Generate a code bit to write to the new config at pos."""

    def write_to(self, pos, value, skip_border=False):
        """Directly write to the next config at pos."""

    def write_to_current(self, pos, value, skip_border=False):
        """Directly write a value to the current config at pos."""

    def read_from(self, pos, skip_border=False):
        """Directly read from the current config at pos."""

    def read_from_next(self, pos, skip_border=False):
        """Directly read from the next config at pos."""

    def get_size(self, dimension=0):
        """Generate a code bit to get the size of the config space in
        the specified dimension"""

    def get_size_of(self, dimension=0):
        """Get the size of the config space in the specified dimension."""

    def multiplicate_config(self):
        """Take the current config "cconf" and multiply it over all
        history slots that need to have duplicates at the beginning."""

    def swap_configs(self):
        """Swap out all configs"""

class CellLoop(WeaveStepFuncVisitor):
    """A CellLoop is responsible for looping over cell space and giving access
    to the current position."""
    def get_pos(self):
        """Returns a code bit to get the current position in config space."""

    def get_iter(self):
        """Returns an iterator for iterating over the config space in python."""

class Neighbourhood(WeaveStepFuncVisitor):
    """A Neighbourhood is responsible for getting states from neighbouring cells."""

    def neighbourhood_cells(self):
        """Get the names of the neighbouring cells."""

    def get_offsets(self):
        """Get the offsets of the neighbourhood cells."""


    def bounding_box(self, steps=1):
        """Find out, how many cells, at most, have to be read after
        a number of steps have been done.

        It will return a list of tuples with relative values where 0 is the
        index of the current cell. It will have a format like:

            [(minX, maxX),
             (minY, maxY),
             (minZ, maxZ),
             ...]"""

class BorderHandler(WeaveStepFuncVisitor):
    """The BorderHandler is responsible for treating the borders of the
    configuration. One example is copying the leftmost border to the rightmost
    border and vice versa or ensuring the border cells are always 0."""

class Computation(WeaveStepFuncVisitor):
    """The Computation is responsible for calculating the result from the data
    gathered from the neighbourhood."""

class BorderSizeEnsurer(BorderHandler):
    """The BorderSizeEnsurer ensures, that - depending on the bounding box
    returned by :meth:`Neighbourhood.bounding_box` - the underlying config
    array is big enough, so that getting the neighbourhood from the outermost
    cells will not access outside the bounds of the array."""
    def new_config(self):
        """Resizes the configuration array."""
        super(BorderSizeEnsurer, self).new_config()
        bbox = self.code.neigh.bounding_box()
        # FIXME if the bbox goes into the positive values, abs is wrong. use the 
        # FIXME correct amount of minus signs instead?
        dims = len(bbox)
        shape = self.target.cconf.shape
        if dims == 1:
            new_conf = np.zeros(shape[0] + abs(bbox[0][0]) + abs(bbox[0][1]))
            new_conf[abs(bbox[0][0]):-abs(bbox[0][1])] = self.target.cconf
        elif dims == 2:
            # TODO figure out how to create slice objects in a general way.
            new_conf = np.zeros((shape[0] + abs(bbox[0][0]) + abs(bbox[0][1]),
                                 shape[1] + abs(bbox[1][0]) + abs(bbox[1][1])))
            new_conf[abs(bbox[0][0]):-abs(bbox[0][1]),
                     abs(bbox[1][0]):-abs(bbox[1][1])] = self.target.cconf
        self.target.cconf = new_conf

class SimpleStateAccessor(StateAccessor):
    """The SimpleStateAccessor offers access to a one-dimensional configuration
    space."""
    size_names = []
    """The names to use in the C code"""
    border_names = []
    """The names of border offsets"""

    def __init__(self, size):
        super(SimpleStateAccessor, self).__init__()
        self.size = size

    def read_access(self, pos, skip_border=False):
        if skip_border:
            return "cconf(%s)" % (pos,)
        return "cconf(%s)" % (", ".join(gen_offset_pos(pos, self.border_names)),)

    def write_access(self, pos, skip_border=False):
        if skip_border:
            return "nconf(%s)" % (pos)
        return "nconf(%s)" % (",".join(gen_offset_pos(pos, self.border_names)),)

    def init_once(self):
        """Set the sizeX const and register nconf and cconf for extraction
        from the targen when running C code."""
        super(SimpleStateAccessor, self).init_once()
        for sizename, size in zip(self.size_names, self.size):
            self.code.consts[sizename] = size
        self.code.attrs.extend(["nconf", "cconf"])

    def bind(self, target):
        """Get the bounding box from the neighbourhood object."""
        super(SimpleStateAccessor, self).bind(target)
        bb = self.code.neigh.bounding_box()
        #mins = [min([abs(b) for b in a]) for a in bb[::2]]
        mins = [abs(a[0]) for a in bb]
        self.border = tuple(mins)

    def visit(self):
        """Take care for result and sizeX to exist in python and C code,
        for the result to be written to the config space and for the configs
        to be swapped by the python code."""
        super(SimpleStateAccessor, self).visit()
        for name, value in zip(self.border_names, self.border):
            self.code.add_code("headers",
                    "#define %s %d" % (name, value))
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

    def read_from(self, pos, skip_border=False):
        if skip_border:
            return self.target.cconf[pos]
        return self.target.cconf[offset_pos(pos, self.border)]

    def read_from_next(self, pos, skip_border=False):
        if skip_border:
            return self.target.nconf[pos]
        return self.target.nconf[offset_pos(pos, self.border)]

    def write_to(self, pos, value, skip_border=False):
        if skip_border:
            self.target.nconf[pos] = value
        else:
            self.target.nconf[offset_pos(pos, self.border)] = value

    def write_to_current(self, pos, value, skip_border=False):
        if skip_border:
            self.target.cconf[pos] = value
        else:
            self.target.cconf[offset_pos(pos, self.border)] = value

    def get_size_of(self, dimension=0):
        return self.size[dimension]

    def swap_configs(self):
        """Swaps nconf and cconf in the target."""
        self.target.nconf, self.target.cconf = \
                self.target.cconf, self.target.nconf

    def multiplicate_config(self):
        """Copy cconf to nconf in the target."""
        self.target.nconf = self.target.cconf.copy()

class LinearStateAccessor(SimpleStateAccessor):
    """The LinearStateAccessor offers access to a one-dimensional configuration
    space."""
    size_names = ["sizeX"]
    border_names = ["BORDER_OFFSET"]

class TwoDimStateAccessor(SimpleStateAccessor):
    """The TwoDimStateAccessor offers access to a two-dimensional configuration
    space."""
    size_names = ["sizeX", "sizeY"]
    border_names = ["LEFT_BORDER", "UPPER_BORDER"]

class LinearCellLoop(CellLoop):
    """The LinearCellLoop iterates over all cells in order from 0 to sizeX."""
    def get_pos(self):
        return "i"

    def visit(self):
        self.code.add_code("loop_begin",
                """for(int i=0; i < sizeX; i++) {""")
        self.code.add_code("loop_end",
                """}""")

    def get_iter(self):
        def generator():
            for i in range(0, self.code.acc.get_size_of()):
                yield (i,)
        return iter(generator())

class TwoDimCellLoop(CellLoop):
    """The TwoDimCellLoop iterates over all cells from left to right, then from
    top to bottom."""
    def get_pos(self):
        return "i", "j"

    def visit(self):
        self.code.add_code("loop_begin",
                """for(int i=0; i < sizeX; i++) {
for(int j=0; i < sizeY; j++) {""")
        self.code.add_code("loop_end",
                """}
}""")

    def get_iter(self):
        def iterator():
            for i in range(0, self.code.acc.get_size_of(0)):
                for j in range(0, self.code.acc.get_size_of(1)):
                    yield (i, j)
        return iter(iterator())

class NondeterministicCellLoopMixin(WeaveStepFuncVisitor):
    """Deriving from a CellLoop and this Mixin will cause every cell to be
    skipped with a given probability"""
    def __init__(self, probab=0.5, random_generator=None, **kwargs):
        """:param probab: The probability of a cell to be computed.
        :param random_generator: If supplied, use this Random object for
                                 random values.

        .. note::
            The random generator will be used directly by the python code, but
            the C code is a bit more complex.

            The C code carries a randseed with it that gets seeded by the
            Python random number generator at the very beginning, then it uses
            the randseed attribute in the target to seed srand. After the
            computation, randseed will be set to rand(), so that the same
            starting seed will still give the same result.

        .. warning::
            If reproducible randomness sequences are desired, do NOT mix the
            pure python and weave inline step functions!"""
        super(NondeterministicCellLoopMixin, self).__init__(**kwargs)
        if random_generator is None:
            self.random = Random()
        else:
            self.random = random_generator
        self.probab = probab

    def get_iter(self):
        """The returned iterator will skip cells with a probability
        of self.probab."""
        basic_iter = super(NondeterministicCellLoopMixin, self).get_iter()
        def generator():
            for pos in basic_iter:
                if self.random.random() < self.probab:
                    yield pos
        return iter(generator())

    def visit(self):
        """Adds C code for handling the randseed and skipping."""
        super(NondeterministicCellLoopMixin, self).visit()
        self.code.add_code("loop_begin",
                """if(rand() >= RAND_MAX * %s) continue;""" % (self.probab))
        self.code.add_code("localvars",
                """srand(randseed(0));""")
        self.code.add_code("after_step",
                """randseed(0) = rand();""")
        self.code.attrs.append("randseed")

    def set_target(self, target):
        """Adds the randseed attribute to the target."""
        super(NondeterministicCellLoopMixin, self).set_target(target)
        # FIXME how do i get the randseed out without using np.array?
        target.randseed = np.array([self.random.random()])

class LinearNondeterministicCellLoop(LinearCellLoop, NondeterministicCellLoopMixin):
    pass

class TwoDimNondeterministicCellLoop(TwoDimCellLoop, NondeterministicCellLoopMixin):
    pass

class SimpleNeighbourhood(Neighbourhood):
    """The SimpleNeighbourhood offers named access to any number of
    neighbouring fields."""
    def __init__(self, names, offsets):
        """:param names: A list of names for the neighbouring cells.
        :param offsets: A list of offsets for each of the neighbouring cells."""
        super(Neighbourhood, self).__init__()
        self.names = tuple(names)
        self.offsets = tuple(offsets)
        assert len(self.names) == len(self.offsets)

    def visit(self):
        """Adds C and python code to get the neighbouring values and stores
        them in local variables."""
        for name, offset in zip(self.names, self.offsets):
            self.code.add_code("pre_compute", "%s = %s;" % (name,
                     self.code.acc.read_access(
                         gen_offset_pos(self.code.loop.get_pos(), offset))))

        self.code.add_code("localvars",
                "int " + ", ".join(self.names) + ";")

        assignments = ["%s = self.acc.read_from(%s)" % (
                name, "offset_pos(pos, %s)" % (offset,))
                for name, offset in zip(self.names, self.offsets)]
        self.code.add_py_hook("pre_compute",
                "\n".join(assignments))

    def neighbourhood_cells(self):
        return self.names

    def get_offsets(self):
        return self.offsets

    def bounding_box(self, steps=1):
        """Calculate a bounding box from a set of offsets.

        The return value will have an outer list with one tuple for
        each dimension. Each dimension will have a min and a max value.

        Supplying the step argument will figure out, how far accesses will
        reach when running step steps.

        >>> a = cagen.SimpleNeighbourhood(list("lmr"), ((-1,), (0,), (1,)))
        >>> a.bounding_box()
        [(-1, 1)]
        >>> a.bounding_box(2)
        [(-2, 2)]
        >>> b = cagen.SimpleNeighbourhood(list("ab"), ((-5, 20), (99, 10)))
        >>> b.bounding_box()
        [(-5, 99), (10, 20)]
        >>> b.bounding_box(10)
        [(-50, 990), (100, 200)]
        """
        # there is at least one offset and that has to have the right number of
        # dimensions already.
        num_dimensions = len(self.offsets[0])

        # initialise the maximums and minimums from the first offset
        maxes = list(self.offsets[0])
        mins = list(self.offsets[0])

        # go through all offsets
        for offset in self.offsets:
            # for each offset, go through all dimensions it has
            for dim in range(num_dimensions):
                maxes[dim] = max(maxes[dim], offset[dim])
                mins[dim] = min(mins[dim], offset[dim])
        maxes = [m * steps for m in maxes]
        mins = [m * steps for m in mins]
        return zip(mins, maxes)

class ElementaryFlatNeighbourhood(SimpleNeighbourhood):
    """This is the neighbourhood used by the elementary cellular automatons.

    The neighbours are called l, m and r for left, middle and right."""
    def __init__(self, **kwargs):
        super(ElementaryFlatNeighbourhood, self).__init__(
                list("lmr"),
                [[-1], [0], [1]], **kwargs)

class VonNeumannNeighbourhood(SimpleNeighbourhood):
    """This is the Von Neumann Neighbourhood, in which the cell itself and the
    left, upper, lower and right neighbours are considered.

    The neighbours are called l, u, m, d and r for left, up, middle, down and
    right respectively."""
    def __init__(self, **kwargs):
        super(VonNeumannNeighbourhood, self).__init__(
                list("lumdr"),
                [(0,-1), (0,1), (-1,0), (1,0), (0,0)],
                **kwargs)

class MooreNeighbourhood(SimpleNeighbourhood):
    """This is the Moore Neighbourhood. The cell and all of its 8 neighbours
    are considered for computation.

    The fields are called lu, u, ru, l, m, r, ld, d and rd for left-up, up,
    right-up, left, middle, right, left-down, down and right-down
    respectively."""

    def __init__(self, **kwargs):
        super(MooreNeighbourhood, self).__init__(
                "lu u ru l m r ld d rd".split(" "),
                list(product([-1, 0, 1], [-1, 0, 1])),
                **kwargs)

class BaseBorderCopier(BorderSizeEnsurer):
    def new_config(self):
        """Copies over the borders once."""
        super(BaseBorderCopier, self).new_config()

        retargetted = "\n".join(self.copy_py_code)
        retargetted = retargetted.replace("self.", "self.code.")
        retargetted = retargetted.replace("write_to(", "write_to_current(")
        retargetted = retargetted.replace("read_from_next(", "read_from(")
        for dim, size_name in enumerate(self.code.acc.size_names):
            size = self.code.acc.get_size_of(dim)
            retargetted = retargetted.replace(size_name, str(size))
        if not HAVE_TUPLE_ARRAY_INDEX:
            retargetted = tuple_array_index_fixup(retargetted)

        exec retargetted in globals(), locals()

    def tee_copy_hook(self, code):
        self.code.add_py_hook("after_step", code)
        self.copy_py_code.append(code)

    def visit(self):
        self.copy_py_code = []
        super(BaseBorderCopier, self).visit()

class SimpleBorderCopier(BaseBorderCopier):
    """Copy over cell values, so that reading from a cell at the border over
    the border yields a sensible result.

    In the case of the SimpleBorderCopier, the borders act like "portals" to
    the opposite side of the field.

    This class should work with any number of dimensions."""
    def visit(self):
        super(SimpleBorderCopier, self).visit()
        # This is the new concept for the border copier:

        # 0) (BorderSizeEnsurer) make the array big enough so that no reads will
        #    ever read outside the array
        # 1) Find out from the bounding box, what areas of the "inner" array are in
        #    need of getting data copied over.
        # 2) Iterate over all those and add all reads to out-of-array positions into
        #    a set. Name that set "outside_reads"
        # 3) Iterate over all outside_reads and figure out where they need to end up.
        #    For instance on the other side of the array, or maybe mirrored or
        #    something entirely different
        # 4) Create a dictionary copy_ops with the positions to copy to as keys and
        #    the positions to copy from as values
        # 5) Maybe/Someday, order the copy ops so that they turn into slices for
        #    numpy or so that they are especially cache efficient or anything
        # 6) Write out code to do these operations in after_step.

        # TODO iterate only over the relevant positions instead of all of them
        dims = len(self.code.neigh.bounding_box())
        neighbours = self.code.neigh.get_offsets()
        self.dimension_sizes = [self.code.acc.get_size_of(dim) for dim in range(dims)]
        ranges = [range(size) for size in self.dimension_sizes]

        if not HAVE_TUPLE_ARRAY_INDEX:
            # more pypy compatibility
            def is_beyond_border(pos):
                dimension, size = pos, self.dimension_sizes[0]
                return (dimension < 0 or dimension >= size)
        else:
            def is_beyond_border(pos):
                for dimension, size in zip(pos, self.dimension_sizes):
                    if dimension < 0 or dimension >= size:
                        return True
                return False

        over_border= {}

        # FIXME Even though sizeX and friends are now variables in the code,
        #       the positions at the edges are still absolute, so even though
        #       sizeX is pumped into the c code from the outside, the right,
        #       lower, ... border positions still cause new C code to be
        #       compiled each time.
        #
        #       Maybe iterating "only over the relevant parts" can help this by
        #       passing the positions not as absolute values, but as relatives
        #       to the relevant sizeFoo variable.
        for pos in product(*ranges):
            for neighbour in neighbours:
                target = offset_pos(pos, neighbour)
                if isinstance(target, int): # pack this into a tuple for pypy
                    target = (target,)
                if is_beyond_border(target):
                    over_border[tuple(target)] = ", ".join(self.wrap_around_border(target))

        copy_code = []

        for write, read in over_border.iteritems():
            copy_code.append("%s = %s;" % (
                self.code.acc.write_access(write),
                self.code.acc.write_access((read,))))

            self.tee_copy_hook("""self.acc.write_to(%s,
    value=self.acc.read_from_next((%s,)))""" % (write, read))

        self.code.add_code("after_step",
                "\n".join(copy_code))

    def wrap_around_border(self, pos):
        """Create a piece of py/c code, that calculates the source for a read
        that would set the right value at position pos, which is beyond the
        border."""
        newpos = []
        for val, size, size_name in zip(pos,
                     self.dimension_sizes, self.code.acc.size_names):
            if val < 0:
                newpos.append("%s + %s" % (size_name, val))
            elif val >= size:
                newpos.append("%s - %s" % (val, size_name))
            else:
                newpos.append("%s" % (val,))
        return tuple(newpos)

class TwoDimZeroReader(BorderSizeEnsurer):
    """This BorderHandler makes sure that zeros will always be read when
    peeking over the border."""
    # there is no extra work at all to be done as compared to the
    # BorderSizeEnsurer, because it embeds the confs into np.zero.

class ElementaryCellularAutomatonBase(Computation):
    max_value = 1
    def __init__(self, rule, **kwargs):
        super(ElementaryCellularAutomatonBase, self).__init__(**kwargs)
        self.rule = rule

    def visit(self):
        super(ElementaryCellularAutomatonBase, self).visit()
        self.neigh = zip(self.code.neigh.get_offsets(), self.code.neigh.neighbourhood_cells())
        self.neigh.sort(key=lambda (offset, name): offset)
        self.digits = len(self.neigh)
        self.base = self.max_value + 1

        compute_code = ["result = 0;"]
        compute_py = ["result = 0"]
        self.code.attrs.append("rule")

        for digit_num, (offset, name) in zip(range(len(self.neigh) - 1, -1, -1), self.neigh):
            code = "result += %s * %d" % (name, self.base ** digit_num)
            compute_code.append(code + ";")
            compute_py.append(code)

        compute_code.append("result = rule(result);")
        compute_py.append("result = self.target.rule[int(result)]")

        self.code.add_code("compute", "\n".join(compute_code))
        self.code.add_py_hook("compute", "\n".join(compute_py))
        print "\n".join(compute_code)
        print "\n".join(compute_py)

    def init_once(self):
        super(ElementaryCellularAutomatonBase, self).init_once()

        entries = self.base ** self.digits
        self.target.rule = np.zeros(entries, int)
        for digit in range(entries):
            if self.rule & (self.base ** digit) > 0:
                self.target.rule[digit] = 1

        # and now do some heavy work to generate a pretty-printer!
        bbox = self.code.neigh.bounding_box()
        offsets = self.code.neigh.get_offsets()
        offset_to_name = dict(self.neigh)
        ordered_names = [a[1] for a in self.neigh]

        if len(bbox) == 1:
            h = 3
            y_offset = None
        else:
            h = bbox[1][1] - bbox[1][0] + 3
            y_offset = bbox[1][0]
        protolines = [[] for i in range(h)]
        lines = [line[:] for line in protolines]
        w = bbox[0][1] + 1 - bbox[0][0]

        for y in range(h):
            for x in range(bbox[0][0], bbox[0][1] + 1):
                if h == 3 and (x,) in offsets and y == 0:
                    lines[y].append("%(" + offset_to_name[(x,)]
                               + ")d")
                elif h > 3 and (x, y + y_offset) in offsets:
                    lines[y].append("%(" + offset_to_name[(x, y + y_offset)]
                               + ")d")
                else:
                    lines[y].append(" ")
            lines[y] = "".join(lines[y]) + "  "

        lines[-1] = ("X".center(w) + "  ").replace("X", "%(result_value)d")

        template = [line[:] for line in lines]

        def pretty_printer(self):
            lines = [line[:] for line in protolines]
            for i in range(self.base ** self.digits):
                values = [1 if (i & (self.base ** k)) > 0 else 0
                        for k in range(len(offsets))]
                asdict = dict(zip(ordered_names, values))
                asdict.update(result_value = self.target.rule[i])

                for line, tmpl_line in zip(lines, template):
                    line.append(tmpl_line % asdict)

            return "\n".join(["".join(line) for line in lines])

            # TODO print the result of each one, too.

        self.pretty_print = new.instancemethod(pretty_printer, self, self.__class__)

    def pretty_print(self):
        """This method is generated upon init_once and pretty-prints the rules
        that this elementary cellular automaton uses for local steps."""

class CountBasedComputationBase(Computation):
    """This base class counts the amount of nonzero neighbours excluding the
    center cell and offers the result as a local variable called
    nonzerocount of type int.

    The name of the central neighbour will be provided as self.central_name."""
    def visit(self):
        super(CountBasedComputationBase, self).visit()
        names = list(self.code.neigh.neighbourhood_cells())
        offsets = self.code.neigh.get_offsets()

        # kick out the center cell, if any.
        zero_offset = tuple([0] * len(offsets[0]))
        zero_position = offsets.index(zero_offset)
        if zero_position != -1:
            self.central_name = names.pop(zero_position)
        else:
            self.central_name = None

        self.code.add_code("localvars", "int nonzerocount;")
        code = "nonzerocount = %s" % (" + ".join(names))

        self.code.add_code("compute", code + ";")
        self.code.add_py_hook("compute", code)

class LifeCellularAutomatonBase(CountBasedComputationBase):
    """This computation base is useful for any life-like step function in which
    the number of ones in the neighbourhood of a cell are counted to decide
    wether to change a 0 into a 1 or the other way around."""
    def __init__(self, reproduce_min=3, reproduce_max=3,
                 stay_alive_min=2, stay_alive_max=3, **kwargs):
        """:param reproduce_min: The minimal number of alive cells needed to
                                 reproduce to this cell.
           :param reproduce_max: The maximal number of alive cells that still
                                 cause a reproduction.
           :param stay_alive_min: The minimal number of alive neighbours needed
                                  for a cell to survive.
           :param stay_alive_max: The maximal number of alive neighbours that
                                  still allow the cell to survive."""
        super(LifeCellularAutomatonBase, self).__init__(**kwargs)
        self.params = dict(reproduce_min = reproduce_min,
                reproduce_max = reproduce_max,
                stay_alive_min = stay_alive_min,
                stay_alive_max = stay_alive_max)

    def visit(self):
        super(LifeCellularAutomatonBase, self).visit()
        assert self.central_name is not None, "Need a neighbourhood with a named zero offset"
        self.params.update(central_name=self.central_name)
        self.code.add_code("compute",
                """if (%(central_name)s == 0) {
      if (nonzerocount >= %(reproduce_min)d && nonzerocount <= %(reproduce_max)d) {
        result = 1;
    }} else {
      if (nonzerocount < %(stay_alive_min)d || nonzerocount > %(stay_alive_max)d) {
        result = 0;
      }}""" % self.params)
        self.code.add_py_hook("compute","""
if %(central_name)s == 0:
    if %(reproduce_min)d <= nonzerocount <= %(reproduce_max)d:
      result = 1
else:
    if not (%(stay_alive_min)d <= nonzerocount <= %(stay_alive_max)d):
      result = 0""" % self.params)

class TestTarget(object):
    """The TestTarget is a simple class that can act as a target for a
    :class:`WeaveStepFunc`."""
    def __init__(self, size=None, config=None, **kwargs):
        """:param size: The size of the config to generate. Alternatively the
                        size of the supplied config.
           :param config: Optionally the config to use."""
        super(TestTarget, self).__init__(**kwargs)
        if config is None:
            assert size is not None
            self.cconf = np.zeros(size)
            rand = Random(11)
            for i in range(size):
                self.cconf[i] = rand.choice([0, 1])
            self.size = size
        else:
            self.cconf = config.copy()
            self.size = self.cconf.shape

    def pretty_print(self):
        """pretty-print the configuration and such"""

class BinRule(TestTarget):
    """A Target plus a WeaveStepFunc for elementary cellular automatons."""
    def __init__(self, size=None, deterministic=True, rule=126, config=None, **kwargs):
        """:param size: The size of the config to generate if no config
                        is supplied.
           :param deterministic: Go over every cell every time or skip cells
                                 randomly?
           :param rule: The rule number for the elementary cellular automaton.
           :param config: Optionally the configuration to use."""
        if size is None:
            size = len(config)
        super(BinRule, self).__init__(size, config, **kwargs)

        self.rule = None
        self.computer = ElementaryCellularAutomatonBase(rule)

        self.stepfunc = WeaveStepFunc(
                loop=LinearCellLoop() if deterministic
                     else LinearNondeterministicCellLoop(),
                accessor=LinearStateAccessor(size=(size,)),
                neighbourhood=SimpleNeighbourhood(list("lmr"), ((-1,), (0,), (1,))),
                extra_code=[SimpleBorderCopier(),
                    self.computer])

        self.stepfunc.set_target(self)
        self.stepfunc.gen_code()

    def step_inline(self):
        """Use the step function to step with weave.inline."""
        self.stepfunc.step_inline()

    def step_pure_py(self):
        """Use the step function to step with pure python code."""
        self.stepfunc.step_pure_py()

    def pretty_print(self):
        return self.computer.pretty_print()

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

    b_l, b_r = bin_rule.stepfunc.neigh.bounding_box()[0]
    pretty_print_array = build_array_pretty_printer(size, abs(b_l), abs(b_r), 20, 20)

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
