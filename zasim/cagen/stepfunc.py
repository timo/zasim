import new

from .utils import dedent_python_code, offset_pos

from ..features import HAVE_WEAVE, HAVE_TUPLE_ARRAY_INDEX, tuple_array_index_fixup

# TODO how do i get functions for pure-py-code in there without making it ugly?
from itertools import product

if HAVE_WEAVE:
    from scipy import weave
    from scipy.weave import converters

EXTREME_PURE_PY_DEBUG = False

class StepFunc(object):
    """The StepFunc composes different parts into a functioning
    step function."""

    neigh = None
    """The :class:`Neighbourhood` object in use."""

    acc = None
    """The :class:`StateAccessor` object in use."""

    loop = None
    """The :class:`CellLoop` object in use."""

    visitors = None
    """All :class:`StepFuncVisitor` objects."""

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
        :param extra_code: Further :class:`StepFuncVisitor` classes, that
                           add more behaviour.
                           Usually at least a :class:`BorderCopier`.
        :param target: The object to target.
        :param size: If the target is not supplied, the size has to be
                     specified here."""

        super(StepFunc, self).__init__(**kwargs)

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
        function = dedent_python_code(function)
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

    def get_config(self):
        return self.target.cconf.copy()

    def set_config(self, config):
        self.target.cconf = config.copy()
        self.new_config()

    def set_config_value(self, pos, value=None):
        """Set the value of the configuration at pos to value.
        If value is None, flip the value that's already there."""
        if value is None:
            value = 1 - self.acc.read_from(pos)
        self.acc.write_to_current(pos, value)

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

    def __str__(self):
        name_parts = []
        for code in self.visitors:
            code.build_name(name_parts)
        return " ".join(name_parts)

