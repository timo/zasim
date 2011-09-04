# coding: utf-8
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

    from zasim.cagen import *
"""

# TODO make it extra hard to change the loop variables using a neighbourhood.

# TODO separate the functions to make C code from the ones that do pure python
#      computation

# TODO figure out how the code should handle resizing of configurations and
#      other such things.

# TODO figure out if scipy.weave.accelerate_tools is any good.

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
from itertools import product, chain
import sys
import new

EXTREME_PURE_PY_DEBUG = False

if HAVE_TUPLE_ARRAY_INDEX:
    def offset_pos(pos, offset):
        """Offset a position by an offset. Any amount of dimensions should work.

        >>> offset_pos((1, ), (5, ))
        (6,)
        >>> offset_pos((1, 2, 3), (9, 8, 7))
        (10, 10, 10)"""
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

    >>> gen_offset_pos(["i", "j"], ["foo", "bar"])
    ['i + foo', 'j + bar']"""
    return ["%s + %s" % (a, b) for a, b in zip(pos, offset)]

class WeaveStepFunc(object):
    """The WeaveStepFunc composes different parts into a functioning
    step function."""

    neigh = None
    """The :class:`Neighbourhood` object in use."""

    acc = None
    """The :class:`StateAccessor` object in use."""

    loop = None
    """The :class:`CellLoop` object in use."""

    visitors = None
    """All :class:`WeaveStepFuncVisitor` objects."""

    target = None
    """The configuration object that is targetted."""

    prepared = False
    """Is the step function ready?"""

    def __init__(self, loop, accessor, neighbourhood, extra_code=[],
                 target=None, size=None, **kwargs):
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
                           Usually at least a :class:`BorderCopier`.
        :param target: The object to target.
        :param size: If the target is not supplied, the size has to be
                     specified here."""

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

        if size is None:
            size = target.cconf.shape
        self.acc.set_size(size)

        self.visitors = [self.acc, self.neigh, self.loop] + extra_code

        for code in self.visitors:
            code.bind(self)

        for code in self.visitors:
            code.visit()

        if target is not None:
            self.set_target(target)

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

        # TODO run the code once with dummy data, that will still cause the
        #      types to match - the only way to compile a function with weave
        #      without running it, too, would be to copy most of the code from
        #      weave.inline_tools.attempt_function_call.

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
        myglob.update(self.consts)
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
        self.prepared = True

    def step_pure_py(self):
        """Run a step using the compiled python code.

        .. note::
            This function will be generated by gen_code."""
        raise ValueError("Cannot run pure python step until gen_code has been"
                         "called")

    def step(self):
        try:
            self.step_inline()
            self.step = self.step_inline
        except:
            print "falling back to pure python step function"

            self.step_pure_py()
            self.step = self.step_pure_py

    def getConf(self):
        return self.target.cconf.copy()

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

    code = None
    """The :class:`WeaveStepFunc` instance this visitor is bound to."""

    target = None
    """The configuration object that is being targetted."""

    def bind(self, code):
        """Bind the visitor to a StepFunc.

        .. note::
            Once bonded, the visitor object will refuse to be rebound."""
        assert self.code is None, "%r is already bound to %r" % (self, self.code)
        self.code = code
    def visit(self):
        """Adds code to the bound step func.

        This will be called directly after bind.

        .. note::
            Never call this function on your own.
            This method will be called by :meth:`WeaveStepFunc.__init__`."""

    def set_target(self, target):
        """Target a CA instance

        .. note::
            Once a target has been set, the visitor object will refuse to retarget."""
        assert self.target is None, "%r already targets %r" % (self, self.target)
        self.target = target

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
    border from the calculation. This is mainly useful for
    :class:`BorderHandler` subclasses."""

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

    def set_size(self, size):
        """Set the size of the target."""

    def gen_copy_code(self):
        """Generate a bit of C code to copy the current field over from the old
        config. This is necessary for instance for nondeterministic step funcs
        combined with swapping two confs around."""

    def gen_copy_py_code(self):
        """Generate a bit of py code to copy the current field over from the
        old config."""

    # TODO this class needs to get a method for generating a view onto the part
    #      of the array inside the borders.

class CellLoop(WeaveStepFuncVisitor):
    """A CellLoop is responsible for looping over cell space and giving access
    to the current position."""
    def get_pos(self):
        """Returns a code bit to get the current position in config space."""

    def get_iter(self):
        """Returns an iterator for iterating over the config space in python."""

class Neighbourhood(WeaveStepFuncVisitor):
    """A Neighbourhood is responsible for getting states from neighbouring cells."""

    names = ()
    """The names of neighbourhood fields."""

    offsets = ()
    """The offsets of neighbourhood fields."""

    def neighbourhood_cells(self):
        """Get the names of the neighbouring cells."""
        return self.names

    def get_offsets(self):
        """Get the offsets of the neighbourhood cells."""
        return self.offsets

    def recalc_bounding_box(self):
        """Recalculate the bounding box."""
        self.bb = ((-99, 100),
                   (-1, 1))

    def bounding_box(self, steps=1):
        """Find out, how many cells, at most, have to be read after
        a number of steps have been done.

        It will return a tuple of tuples with relative values where 0 is the
        index of the current cell. It will have a format like:

            ((minX, maxX),
             (minY, maxY),
             (minZ, maxZ),
             ...)"""
        if steps == 1:
            return self.bb
        else:
            return tuple((low * steps, high * steps) for (low, high) in self.bb)

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
        borders = self.code.acc.border_size
        dims = len(bbox)
        shape = self.target.cconf.shape
        if dims == 1:
            (left,), (right,) = self.code.acc.border_names
            new_conf = np.zeros(shape[0] + borders[left] + borders[right], int)
            new_conf[borders[left]:-borders[right]] = self.target.cconf
        elif dims == 2:
            # TODO figure out how to create slice objects in a general way.
            (left,up), (right,down) = self.code.acc.border_names
            new_conf = np.zeros((shape[0] + borders[left] + borders[right],
                                 shape[1] + borders[up] + borders[down]), int)
            new_conf[borders[left]:-borders[right],
                     borders[up]:-borders[down]] = self.target.cconf
        self.target.cconf = new_conf

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

    def __init__(self, **kwargs):
        super(SimpleStateAccessor, self).__init__(**kwargs)

    def set_size(self, size):
        super(SimpleStateAccessor, self).set_size(size)
        self.size = size

    def read_access(self, pos, skip_border=False):
        if skip_border:
            return "cconf(%s)" % (pos,)
        return "cconf(%s)" % (", ".join(gen_offset_pos(pos, self.border_names[0])),)

    def write_access(self, pos, skip_border=False):
        if skip_border:
            return "nconf(%s)" % (pos)
        return "nconf(%s)" % (",".join(gen_offset_pos(pos, self.border_names[0])),)

    def init_once(self):
        """Set the sizeX const and register nconf and cconf for extraction
        from the targen when running C code."""
        super(SimpleStateAccessor, self).init_once()
        for sizename, size in zip(self.size_names, self.size):
            self.code.consts[sizename] = size
        self.code.attrs.extend(["nconf", "cconf"])

    def bind(self, target):
        """Get the bounding box from the neighbourhood object,
        set consts for borders."""
        super(SimpleStateAccessor, self).bind(target)
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

    def read_from(self, pos, skip_border=False):
        if skip_border:
            return self.target.cconf[pos]
        return self.target.cconf[offset_pos(pos, self.border[0])]

    def read_from_next(self, pos, skip_border=False):
        if skip_border:
            return self.target.nconf[pos]
        return self.target.nconf[offset_pos(pos, self.border[0])]

    def write_to(self, pos, value, skip_border=False):
        if skip_border:
            self.target.nconf[pos] = value
        else:
            self.target.nconf[offset_pos(pos, self.border[0])] = value

    def write_to_current(self, pos, value, skip_border=False):
        if skip_border:
            self.target.cconf[pos] = value
        else:
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

class LinearStateAccessor(SimpleStateAccessor):
    """The LinearStateAccessor offers access to a one-dimensional configuration
    space."""
    size_names = ("sizeX",)
    border_names = (("LEFT_BORDER",), ("RIGHT_BORDER",))

class TwoDimStateAccessor(SimpleStateAccessor):
    """The TwoDimStateAccessor offers access to a two-dimensional configuration
    space."""
    size_names = ("sizeX", "sizeY")
    border_names = (("LEFT_BORDER", "UPPER_BORDER"), ("RIGHT_BORDER", "LOWER_BORDER"))

class SimpleHistogram(WeaveStepFuncVisitor):
    """Adding this class to the extra code list of a :class:`WeaveStepFunc` will
    give access to a new array in the target called "histogram". This value will
    count the amount of cells with the value used as its index."""
    def visit(self):
        super(SimpleHistogram, self).visit()
        if len(self.code.acc.size_names) == 1:
            center_name = self.code.neigh.names[self.code.neigh.offsets.index((0,))]
        else:
            center_name = self.code.neigh.names[self.code.neigh.offsets.index((0, 0))]
        self.code.add_code("post_compute",
                """if (result != %(center)s) { histogram(result) += 1; histogram(%(center)s) -= 1; }""" % dict(center=center_name))

        self.code.add_py_hook("post_compute",
                """# update the histogram
if result != %(center)s:
    self.target.histogram[result] += 1
    self.target.histogram[int(%(center)s)] -= 1""" % dict(center=center_name))

    def regenerate_histogram(self):
        conf = self.target.cconf
        acc = self.code.acc
        if len(acc.size_names) == 1:
            conf = conf[acc.border_size[acc.border_names[0][0]]:
                       -acc.border_size[acc.border_names[1][0]]]
        elif len(self.code.acc.size_names) == 2:
            conf = conf[acc.border_size[acc.border_names[0][0]]:
                       -acc.border_size[acc.border_names[1][0]],
                       acc.border_size[acc.border_names[0][1]]:
                       -acc.border_size[acc.border_names[1][1]]]
            # make the configuration 1d for bincount.
            conf = np.ravel(conf)
        else:
            raise NotImplementedError("Can only handle 1d or 2d arrays")
        self.target.histogram = np.bincount(conf)

    def new_config(self):
        """Create a starting histogram."""
        super(SimpleHistogram, self).new_config()
        self.regenerate_histogram()

    def init_once(self):
        """Set up the histogram attributes."""
        super(SimpleHistogram, self).init_once()
        self.code.attrs.extend(["histogram"])

class ActivityRecord(WeaveStepFuncVisitor):
    """Adding this class to the extra code list of a :class:`WeaveStepFunc` will
    create a property called "activity" on the target. It is a single-cell
    array with the value of how many fields have changed their state in the last
    step.

    A value of -1 stands for "no data"."""
    def visit(self):
        super(ActivityRecord, self).visit()
        if len(self.code.acc.size_names) == 1:
            center_name = self.code.neigh.names[self.code.neigh.offsets.index((0,))]
        else:
            center_name = self.code.neigh.names[self.code.neigh.offsets.index((0, 0))]
        self.code.add_code("localvars",
                """activity(0) = 0;""")
        self.code.add_code("post_compute",
                """if (result != %(center)s) { activity(0) += 1; }""" % dict(center=center_name))

        self.code.add_py_hook("init",
                """self.target.activity[0] = 0""")
        self.code.add_py_hook("post_compute",
                """# count up the activity
if result != %(center)s:
    self.target.activity[0] += 1""" % dict(center=center_name))

    def new_config(self):
        """Reset the activity counter to -1, which stands for "no data"."""
        super(ActivityRecord, self).new_config()
        self.target.activity = np.array([-1])

    def init_once(self):
        """Set up the activity attributes."""
        super(ActivityRecord, self).init_once()
        self.code.attrs.extend(["activity"])

class LinearCellLoop(CellLoop):
    """The LinearCellLoop iterates over all cells in order from 0 to sizeX."""
    def get_pos(self):
        return "i"

    def visit(self):
        super(LinearCellLoop, self).visit()
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

class NondeterministicCellLoopMixin(WeaveStepFuncVisitor):
    """Deriving from a CellLoop and this Mixin will cause every cell to be
    skipped with a given probability"""

    probab = 0.5
    """The probability with which to execute each cell."""

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

    def visit(self):
        """Adds C code for handling the randseed and skipping."""
        super(NondeterministicCellLoopMixin, self).visit()
        self.code.add_code("loop_begin",
                """if(rand() >= RAND_MAX * %(probab)s) {
                    %(copy_code)s
                    continue;
                };""" % dict(probab=self.probab,
                    copy_code=self.code.acc.gen_copy_code(),
                    ))
        self.code.add_code("localvars",
                """srand(randseed(0));""")
        self.code.add_code("after_step",
                """randseed(0) = rand();""")
        self.code.attrs.append("randseed")

        self.code.add_py_hook("pre_compute",
                """if self.random.random() >= %(probab)f:
    %(copy_code)s
    continue""" % dict(probab=self.probab,
                       copy_code=self.code.acc.gen_copy_py_code()))

    def set_target(self, target):
        """Adds the randseed attribute to the target."""
        super(NondeterministicCellLoopMixin, self).set_target(target)
        # FIXME how do i get the randseed out without using np.array?
        target.randseed = np.array([self.random.random()])

    def bind(self, stepfunc):
        super(NondeterministicCellLoopMixin, self).bind(stepfunc)
        stepfunc.random = self.random

class LinearNondeterministicCellLoop(NondeterministicCellLoopMixin,LinearCellLoop):
    """This Nondeterministic Cell Loop loops over one dimension, skipping cells
    with a probability of probab."""
    pass

class TwoDimNondeterministicCellLoop(NondeterministicCellLoopMixin, TwoDimCellLoop):
    """This Nondeterministic Cell Loop loops over two dimensions, skipping cells
    with a probability of probab."""
    pass

class SimpleNeighbourhood(Neighbourhood):
    """The SimpleNeighbourhood offers named access to any number of
    neighbouring fields with any number of dimensions."""

    names = ()
    """The names of neighbourhood fields."""

    offsets = ()
    """The offsets of neighbourhood fields."""

    def __init__(self, names, offsets):
        """:param names: A list of names for the neighbouring cells.
        :param offsets: A list of offsets for each of the neighbouring cells."""
        super(Neighbourhood, self).__init__()
        self.names = tuple(names)
        self.offsets = tuple([tuple(offset) for offset in offsets])
        assert len(self.names) == len(self.offsets)
        self.recalc_bounding_box()

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

    def recalc_bounding_box(self):
        """Calculate a bounding box from a set of offsets."""
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

        self.bb = tuple(zip(mins, maxes))

    def bounding_box(self, steps=1):
        """Get the bounding box resulting from step successive reads.

        The return value will have an outer tuple with one tuple for
        each dimension. Each dimension will have a min and a max value.

        >>> a = SimpleNeighbourhood(list("lmr"), ((-1,), (0,), (1,)))
        >>> a.bounding_box()
        ((-1, 1),)
        >>> a.bounding_box(2)
        ((-2, 2),)
        >>> b = SimpleNeighbourhood(list("ab"), ((-5, 20), (99, 10)))
        >>> b.bounding_box()
        ((-5, 99), (10, 20))
        >>> b.bounding_box(10)
        ((-50, 990), (100, 200))
        """
        return super(SimpleNeighbourhood, self).bounding_box(steps)

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
    """This base class for border copiers executes a retargetted version of the
    pure-py code,that was generated for ensuring the borders are neat after a
    full step, when new_config is called.

    .. note::
        In order for this to work you have to use :meth:`tee_copy_hook` instead
        of :meth:`WeaveStepFunc.add_py_hook` for creating the border fixup
        code, so that it can be retargetted and reused."""
    def visit(self):
        """Initialise :attr:`copy_py_code`."""
        self.copy_py_code = []
        super(BaseBorderCopier, self).visit()

    def new_config(self):
        """Runs the retargetted version of the border copy code created in
        :meth:`visit`."""
        super(BaseBorderCopier, self).new_config()

        retargetted = "\n".join(self.copy_py_code)
        retargetted = retargetted.replace("self.", "self.code.")
        retargetted = retargetted.replace("write_to(", "write_to_current(")
        retargetted = retargetted.replace("read_from_next(", "read_from(")
        for dim, size_name in enumerate(self.code.acc.size_names):
            size = self.code.acc.get_size_of(dim)
            retargetted = retargetted.replace(size_name, str(size))
        for border_name, border_size in self.code.acc.border_size.iteritems():
            retargetted = retargetted.replace(border_name, str(border_size))
        if not HAVE_TUPLE_ARRAY_INDEX:
            retargetted = tuple_array_index_fixup(retargetted)

        exec retargetted in globals(), locals()

    def tee_copy_hook(self, code):
        """Append a piece of code to the "after_step" hook as well as the local
        code piece that gets retargetted and run in :meth:`new_config`."""
        self.code.add_py_hook("after_step", code)
        self.copy_py_code.append(code)

class SimpleBorderCopier(BaseBorderCopier):
    """Copy over cell values, so that reading from a cell at the border over
    the border yields a sensible result.

    In the case of the SimpleBorderCopier, the borders act like "portals" to
    the opposite side of the field.

    This class should work with any number of dimensions."""
    def visit(self):
        """Generate code for copying over or otherwise handling data from the
        borders."""
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

        bbox = self.code.neigh.bounding_box()
        dims = len(bbox)
        neighbours = self.code.neigh.get_offsets()
        self.dimension_sizes = [self.code.acc.get_size_of(dim) for dim in range(dims)]

        slices = []
        # get only the values from the borders in a lazy manner
        #
        # this is the way it works:
        # select the dimension to consider the borders of. (dim)
        # all other dimensions will be considered fully.
        # then go through all dimensions. (subdim)
        # if subdim == dim, only put in the values at the borders
        # else, put in all values

        # TODO change this, so that it uses the accessors border_size property.
        for dim in range(dims):
            slices.append(product(*[range(0, self.dimension_sizes[sd]) if sd != dim else
                                chain(range(0, abs(bbox[dim][1])),
                                      range(self.dimension_sizes[sd] - abs(bbox[dim][0]),
                                            self.dimension_sizes[sd]))
                                for sd in range(dims)]))
        # now we have a lot of product iterators in a list. we want to chain
        # these lists together, so they form one long iterator.
        slices = chain(*slices)

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

        for pos in slices:
            for neighbour in neighbours:
                target = offset_pos(pos, neighbour)
                if isinstance(target, int): # pack this into a tuple for pypy
                    target = (target,)
                if is_beyond_border(target):
                    over_border[tuple(target)] = self.wrap_around_border(target)

        copy_code = []

        for write, read in over_border.iteritems():
            copy_code.append("%s = %s;" % (
                self.code.acc.write_access(write),
                self.code.acc.write_access(read)))

            self.tee_copy_hook("""self.acc.write_to(%s,
    value=self.acc.read_from_next((%s,)))""" % (write, ", ".join(read)))

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

class TwoDimSlicingBorderCopier(BaseBorderCopier):
    """This class copies, with only little code, each side to the opposite
    side. It only works on two-dimensional configurations."""
    def visit(self):
        """Generate code for copying over or otherwise handling data from the
        borders."""
        super(TwoDimSlicingBorderCopier, self).visit()

        self.tee_copy_hook("""# copy the upper portion below the lower border
for pos in product(range(0, sizeX), range(0, LOWER_BORDER)):
    self.acc.write_to((pos[0], sizeY + pos[1]),
            self.acc.read_from_next(pos))""")

        self.tee_copy_hook("""# copy the lower portion above the upper border
for pos in product(range(0, sizeX), range(0, UPPER_BORDER)):
    self.acc.write_to((pos[0], -pos[1] - 1),
            self.acc.read_from_next((pos[0], sizeY - pos[1] - 1)))""")

        self.tee_copy_hook("""# copy the left portion right of the right border
for pos in product(range(0, RIGHT_BORDER), range(0, sizeY)):
    self.acc.write_to((sizeX + pos[0], pos[1]),
            self.acc.read_from_next(pos))""")

        self.tee_copy_hook("""# copy the right portion left of the left border
for pos in product(range(0, LEFT_BORDER), range(0, sizeY)):
    self.acc.write_to((-pos[0] - 1, pos[1]),
            self.acc.read_from_next((sizeX - pos[0] - 1, pos[1])))""")


        self.tee_copy_hook("""# copy the lower left part to the upper right corner
for pos in product(range(0, RIGHT_BORDER), range(0, UPPER_BORDER)):
    self.acc.write_to((sizeX + pos[0], -UPPER_BORDER + pos[1]),
            self.acc.read_from_next((pos[0], sizeY - UPPER_BORDER + pos[1])))""")

        self.tee_copy_hook("""# copy the upper right corner to the lower left corner
for pos in product(range(0, LEFT_BORDER), range(0, LOWER_BORDER)):
    self.acc.write_to((-LEFT_BORDER + pos[0], sizeY + pos[1]),
            self.acc.read_from_next((sizeX - RIGHT_BORDER + pos[0], pos[1])))""")

        self.tee_copy_hook("""# copy the lower right part to the upper left corner
for pos in product(range(0, LEFT_BORDER), range(0, UPPER_BORDER)):
    self.acc.write_to((-LEFT_BORDER + pos[0], -UPPER_BORDER + pos[1]),
            self.acc.read_from_next((-LEFT_BORDER + sizeX + pos[0], -UPPER_BORDER + sizeX + pos[1])))""")

        self.tee_copy_hook("""# copy the upper left part to the lower right corner
for pos in product(range(0, RIGHT_BORDER), range(0, LOWER_BORDER)):
    self.acc.write_to((sizeX + pos[0], sizeY + pos[1]),
            self.acc.read_from_next((pos[0], pos[1])))""")

        # and now for the fun part ...

        copy_code = []
        copy_code.append("int x, y;")

        # upper part to lower border
        copy_code.append("""for(x = 0; x < sizeX; x++) {
    for(y = 0; y < LOWER_BORDER; y++) {
        %s = %s;
    } }""" % (self.code.acc.write_access(("x", "sizeY + y")),
              self.code.acc.write_access(("x", "y")) ))

        # lower part to upper border
        copy_code.append("""for(x = 0; x < sizeX; x++) {
    for(y = 0; y < UPPER_BORDER; y++) {
        %s = %s;
    } }""" % (self.code.acc.write_access(("x", "-y - 1")),
              self.code.acc.write_access(("x", "sizeY - y - 1"))))


        # left part to right border
        copy_code.append("""for(x = 0; x < RIGHT_BORDER; x++) {
    for(y = 0; y < sizeY; y++) {
        %s = %s;
    } }""" % (self.code.acc.write_access(("sizeX + x", "y")),
              self.code.acc.write_access(("x", "y")) ))

        # right part to left border
        copy_code.append("""for(x = 0; x < LEFT_BORDER; x++) {
    for(y = 0; y < sizeY; y++) {
        %s = %s;
    } }""" % (self.code.acc.write_access(("-x - 1", "y")),
              self.code.acc.write_access(("sizeX - x - 1", "y"))))


        # copy the upper left part to the lower right corner
        copy_code.append("""for(x = 0; x < RIGHT_BORDER; x++) {
    for(y = 0; y < LOWER_BORDER; y++) {
        %s = %s;
    } }""" % (self.code.acc.write_access(("sizeX + x", "sizeY + y")),
              self.code.acc.write_access(("x", "y"))))

        # copy the upper right part to the lower left corner
        copy_code.append("""for(x = 0; x < LEFT_BORDER; x++) {
    for(y = 0; y < LOWER_BORDER; y++) {
        %s = %s;
    } }""" % (self.code.acc.write_access(("-LEFT_BORDER + x", "sizeY + y")),
              self.code.acc.write_access(("sizeX - RIGHT_BORDER + x", "y"))))

        # copy the lower right part to the upper left corner
        copy_code.append("""for(x = 0; x < LEFT_BORDER; x++) {
    for(y = 0; y < UPPER_BORDER; y++) {
        %s = %s;
    } }""" % (self.code.acc.write_access(("-LEFT_BORDER + x", "-UPPER_BORDER + y")),
              self.code.acc.write_access(("-LEFT_BORDER + sizeX + x", "-UPPER_BORDER + sizeY + y"))))

        # copy the lower left part to the upper right corner
        copy_code.append("""for(x = 0; x < RIGHT_BORDER; x++) {
    for(y = 0; y < UPPER_BORDER; y++) {
        %s = %s;
    } }""" % (self.code.acc.write_access(("sizeX + x", "-UPPER_BORDER + y")),
              self.code.acc.write_access(("x", "sizeY - UPPER_BORDER + y"))))

        self.code.add_code("after_step",
                "\n".join(copy_code))

class TwoDimZeroReader(BorderSizeEnsurer):
    """This BorderHandler makes sure that zeros will always be read when
    peeking over the border."""
    # there is no extra work at all to be done as compared to the
    # BorderSizeEnsurer, because it already just embeds the confs into
    # np.zero and does that for one or two dimensions.

class ElementaryCellularAutomatonBase(Computation):
    """Infer a 'Gödel numbering' from the used :class:`Neighbourhood` and
    create a computation that corresponds to the rule'th possible combination
    of values for the neighbourhood cells.

    This works with any number of dimensions."""

    # TODO get this from target.possible_values instead?
    base = 2
    """The number of different values each cell can have."""

    rule = 0
    """The elementary cellular automaton rule to use.

    See :meth:`visit` for details on how it's used."""

    def __init__(self, rule, **kwargs):
        super(ElementaryCellularAutomatonBase, self).__init__(**kwargs)
        self.rule = rule

    def visit(self):
        """Get the rule'th cellular automaton for the given neighbourhood.

        First, find out, how many possible combinations there are.
        That's simply the nuber of cells in the neighbourhood as the exponent
        of :attr:`base`.
        Then, normalise the neighbourhood cells by sorting their positions
        first by X, then by Y axis.
        Finally, create code, that sums up all the values and looks up the
        target value from the rule lookup array.
        """
        super(ElementaryCellularAutomatonBase, self).visit()

        self.neigh = zip(self.code.neigh.get_offsets(), self.code.neigh.neighbourhood_cells())
        self.neigh.sort(key=lambda (offset, name): offset)
        self.digits = len(self.neigh)

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

    def init_once(self):
        """Generate the rule lookup array and a pretty printer."""
        super(ElementaryCellularAutomatonBase, self).init_once()
        entries = self.base ** self.digits
        self.target.rule = np.zeros(entries, int)
        for digit in range(entries):
            if self.rule & (self.base** digit) > 0:
                self.target.rule[digit] = 1

        # and now do some heavy work to generate a pretty-printer!
        bbox = self.code.neigh.bounding_box()
        offsets = self.code.neigh.get_offsets()
        offset_to_name = dict(self.neigh)
        ordered_names = [a[1] for a in self.neigh]

        if len(bbox) == 1:
            h = 3
            y_offset = None
        elif len(bbox) == 2:
            h = bbox[1][1] - bbox[1][0] + 3
            y_offset = bbox[1][0]
        else:
            # for higher dimensions, just fall back to the dummy pretty-printer
            return
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

        self.pretty_print = new.instancemethod(pretty_printer, self, self.__class__)

    def pretty_print(self):
        """This method is generated upon init_once and pretty-prints the rules
        that this elementary cellular automaton uses for local steps."""
        return ["cannot pretty-print with neighbourhoods of more than",
                "two dimensions"]

class CountBasedComputationBase(Computation):
    """This base class counts the amount of nonzero neighbours excluding the
    center cell and offers the result as a local variable called
    nonzerocount of type int.

    The name of the central neighbour will be provided as self.central_name.

    .. warning::
        If the values are not limited to 0 and 1, the value of nonzerocount
        will be the sum of the neighbourhood cells values, rather than the
        count of nonzero neighbourhood cells."""

    def visit(self):
        """Generate code that calculates nonzerocount from all neighbourhood
        values."""
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
    """This computation base is useful for any game-of-life-like step function
    in which the number of ones in the neighbourhood of a cell are counted to
    decide wether to change a 0 into a 1 or the other way around."""

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
        """Generates the code that turns a 0 into a 1 if nonzerocount exceeds
        reproduce_min and doesn't exceed reproduce_max and turns a 1 into a 0
        if nonzerocount is lower than stay_alive_min or higher than
        stay_alive_max."""
        super(LifeCellularAutomatonBase, self).visit()
        assert self.central_name is not None, "Need a neighbourhood with a named zero offset"
        self.params.update(central_name=self.central_name)
        self.code.add_code("compute",
                """
    result = %(central_name)s;
    if (%(central_name)s == 0) {
      if (nonzerocount >= %(reproduce_min)d && nonzerocount <= %(reproduce_max)d) {
        result = 1;
    }} else {
      if (nonzerocount < %(stay_alive_min)d || nonzerocount > %(stay_alive_max)d) {
        result = 0;
      }}""" % self.params)
        self.code.add_py_hook("compute","""
result = %(central_name)s
if %(central_name)s == 0:
    if %(reproduce_min)d <= nonzerocount <= %(reproduce_max)d:
      result = 1
else:
    if not (%(stay_alive_min)d <= nonzerocount <= %(stay_alive_max)d):
      result = 0""" % self.params)

CELL_SHADOW, CELL_FULL = "%#"
BACK_SHADOW, BACK_FULL = ", "
def build_array_pretty_printer(size, border, extra=((0, 0),)):
    """Generate a function that pretty-prints a configuration together with its
    border and additional fields from beyond the border.

    :attr size: A tuple describing the size of the configuration.
    :attr border: The amount of cells on each side of the configuration
                  that are beyond the border. It is formed just like the
                  output of :meth:`Neighbourhood.bounding_box`, but all values
                  have to be positive.
    :attr extra: The amount of fields to copy over in addition to the border.

    .. warning ::
        If any BorderHandler is used, that does not simply copy over fields
        from beyond the border, the output with a border or extra cells will be
        wrong!"""
    if len(extra) == 1:
        extra = (extra[0], (0, 0))
    if len(border) == 1:
        border = (border[0], (0, 0))
    def pretty_print_line(arr, sizex=size[0],
            border_left=border[0][0], border_right=border[0][1],
            extra_left=extra[0][0], extra_right=extra[0][1]):

        for cell in arr[sizex - extra_left - border_left - border_right:
                        sizex - border_right]:
            sys.stdout.write(CELL_SHADOW if cell > 0.5 else BACK_SHADOW)
        for cell in arr[border_left:sizex - border_right]:
            sys.stdout.write(CELL_FULL if cell > 0.5 else BACK_FULL)
        for cell in arr[border_left:border_left + border_right + extra_right]:
            sys.stdout.write(CELL_SHADOW if cell > 0.5 else BACK_SHADOW)
        sys.stdout.write("\n")

    if len(size) == 1:
        assert size[0] - extra[0][0] - border[0][0] - border[0][1] >= 0,\
                """Cannot put this much extra on the left"""
        assert border[0][0] + border[0][1] + extra[0][1] <= size[0],\
                """Cannot put this much extra on the left"""
        return pretty_print_line
    elif len(size) == 2:
        if extra != ((0, 0), (0, 0)):
            raise NotImplementedError("Can only pretty-print 2d without"
                                 "extra fields.")
        def pretty_print_array(arr):
            linesize = size[0]
            # draw the first and last lines as if the size were 0, but the
            # border was all of the arrays content. this way we'll get shadow
            # cells drawn above and below the arrays content.
            for y in range(0, border[1][0]):
                pretty_print_line(arr[y], linesize, linesize, 0, 0)
            for y in range(border[1][0], size[1] - border[1][1]):
                pretty_print_line(arr[y])
            for y in range(size[1] - border[1][1], size[1]):
                pretty_print_line(arr[y], linesize, linesize, 0, 0)

        return pretty_print_array
    else:
        raise NotImplementedError("Can't handle arrays of %d dimensions yet" %\
                             len(size))

class TestTarget(object):
    """The TestTarget is a simple class that can act as a target for a
    :class:`WeaveStepFunc`."""

    cconf = None
    """The current config the cellular automaton works on."""

    nconf = None
    """During the step, this is the 'next configuration', otherwise it's the
    previous configuration, because nconf and cconf are swapped after steps."""

    possible_states = [0, 1]
    """What values the cells can have."""

    def __init__(self, size=None, config=None, **kwargs):
        """:param size: The size of the config to generate. Alternatively the
                        size of the supplied config.
           :param config: Optionally the config to use."""
        super(TestTarget, self).__init__(**kwargs)
        if config is None:
            assert size is not None
            self.cconf = np.zeros(size, int)
            rand = Random()
            if HAVE_TUPLE_ARRAY_INDEX:
                for pos in product(*[range(siz) for siz in size]):
                    self.cconf[pos] = rand.choice([0, 1])
            else:
                if len(size) != 1:
                    raise NotImplementedError("Can only create random configs"\
                            "in %dd with HAVE_TUPLE_ARRAY_INDEX." % len(size))
                for pos in range(size[0]):
                    self.cconf[pos] = rand.choice([0, 1])
            self.size = size
        else:
            self.cconf = config.copy()
            self.size = self.cconf.shape

    def pretty_print(self):
        """pretty-print the configuration and such"""

class BinRule(TestTarget):
    """A Target plus a WeaveStepFunc for elementary cellular automatons."""

    rule = None
    """The number of the elementary cellular automaton to simulate."""

    def __init__(self, size=None, deterministic=True, histogram=False, activity=False, rule=126, config=None, **kwargs):
        """:param size: The size of the config to generate if no config
                        is supplied. Must be a tuple.
           :param deterministic: Go over every cell every time or skip cells
                                 randomly?
           :param histogram: Generate and update a histogram as well?
           :param rule: The rule number for the elementary cellular automaton.
           :param config: Optionally the configuration to use."""
        if size is None:
            size = config.shape
        super(BinRule, self).__init__(size, config, **kwargs)

        self.rule = None
        self.computer = ElementaryCellularAutomatonBase(rule)

        self.stepfunc = WeaveStepFunc(
                loop=LinearCellLoop() if deterministic
                     else LinearNondeterministicCellLoop(),
                accessor=LinearStateAccessor(),
                neighbourhood=ElementaryFlatNeighbourhood(),
                extra_code=[SimpleBorderCopier(),
                    self.computer] +
                ([SimpleHistogram()] if histogram else []) +
                ([ActivityRecord()] if activity else []), target=self)

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
    size = 75

    bin_rule = BinRule((size,), rule=105, histogram=True, activity=True)

    b_l, b_r = bin_rule.stepfunc.neigh.bounding_box()[0]
    pretty_print_array = build_array_pretty_printer((size,), ((abs(b_l), abs(b_r)),), ((0, 0),))


    if USE_WEAVE:
        print "weave"
        for i in range(100):
            bin_rule.step_inline()
            pretty_print_array(bin_rule.cconf)
            print bin_rule.histogram, bin_rule.activity
    else:
        print "pure"
        for i in range(100):
            bin_rule.step_pure_py()
            pretty_print_array(bin_rule.cconf)
            print bin_rule.histogram, bin_rule.activity

if __name__ == "__main__":
    if "pure" in sys.argv:
        USE_WEAVE = False
    test()
