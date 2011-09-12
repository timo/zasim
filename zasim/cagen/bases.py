class StepFuncVisitor(object):
    """Base class for step function visitor objects."""

    category = "base"
    """The category this object and its subclasses belong to."""

    code = None
    """The :class:`StepFunc` instance this visitor is bound to."""

    target = None
    """The configuration object that is being targetted."""

    requires_features = []
    provides_features = []
    incompatible_features = []

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
            This method will be called by :meth:`StepFunc.__init__`."""

    def set_target(self, target):
        """Target a CA instance

        .. note::
            Once a target has been set, the visitor object will refuse to retarget."""
        assert self.target is None, "%r already targets %r" % (self, self.target)
        self.target = target

    def init_once(self):
        """Initialize data on the target.

        This function will be called when the :class:`StepFunc` has
        first had its target set."""

    def new_config(self):
        """Check and sanitize a new config.

        This is pure python code that runs when a new config is loaded.
        it only changes the current configuration "cconf" of the automaton.
        after all new_config hooks have been run, they are multiplied."""

    def build_name(self, parts):
        """Add text to the name of the StepFunc for easy identification of
        what's going on."""

class StateAccessor(StepFuncVisitor):
    """A StateAccessor will supply read and write access to the state array.

    It also knows things about how the config space is shaped and sized and
    how to handle swapping or history of configs.

    Additionally, it knows how far to offset reads and writes, so that cells at
    the lowest coordinates will have a border of data around them."""

    category = "accessor"
    """The category this object and its subclasses belong to."""

    def read_access(self, pos):
        """Generate a bit of C code for reading from the old config at pos."""

    def write_access(self, pos):
        """Generate a code bit to write to the new config at pos."""

    def write_to(self, pos, value):
        """Directly write to the next config at pos."""

    def write_to_current(self, pos, value):
        """Directly write a value to the current config at pos."""

    def read_from(self, pos):
        """Directly read from the current config at pos."""

    def read_from_next(self, pos):
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

class CellLoop(StepFuncVisitor):
    """A CellLoop is responsible for looping over cell space and giving access
    to the current position."""

    category = "loop"

    def get_pos(self):
        """Returns a code bit to get the current position in config space."""

    def get_iter(self):
        """Returns an iterator for iterating over the config space in python."""

class Neighbourhood(StepFuncVisitor):
    """A Neighbourhood is responsible for getting states from neighbouring cells.

    :attr:`names` and :attr:`offsets` are sorted by the position of the offset,
    starting at the top-left (negative X, negative Y), going down through
    ascending Y values, then to the next X value.

    .. note ::
        If you subclass from Neighbourhood, all you have to do to get the
        sorting right is to call :meth:`_sort_names_offsets`."""

    category = "neighbourhood"

    names = ()
    """The names of neighbourhood fields."""

    offsets = ()
    """The offsets of neighbourhood fields."""

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

    def _sort_names_offsets(self):
        """Brings the offsets into the right order."""
        pairs = zip(self.offsets, self.names)
        pairs.sort(key=lambda (o, n): o)
        # this essentially unzips the pairs again.
        self.offsets, self.names = zip(*pairs)

class BorderHandler(StepFuncVisitor):
    """The BorderHandler is responsible for treating the borders of the
    configuration. One example is copying the leftmost border to the rightmost
    border and vice versa or ensuring the border cells are always 0."""

    category = "borderhandler"

class Computation(StepFuncVisitor):
    """The Computation is responsible for calculating the result from the data
    gathered from the neighbourhood."""

    category = "computation"

class ExtraStats(StepFuncVisitor):
    """Empty base class for histograms, activity counters, ..."""

    category = "extrastats"

