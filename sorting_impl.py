from zasim.cagen import *
from zasim.simulator import *
from zasim.display.console import *

class Grid(object):
    pass

class Grid1DEuclidean(Grid):
    border = None
    acc = None
    loop = None
    size = []
    neighbourhood = ""
    neigh_names = ()

    def __init__(self):
        self.loop = OneDimCellLoop()

    def use_von_neumann_neighbourhood(self, radius=1):
        assert radius == 1
        self.neighbourhood = "von_neumann"

        # XXX mittlere namen
        class NeighHandle(object):
            def compass_names(foo):
                print "compass names for ", self
                self.neigh_names = ("w", "m", "e")
            def direction_names(foo):
                print "direction names for ", self
                self.neigh_names = ("left", "center", "right")
            def ordering_names(foo):
                print "ordering names for ", self
                self.neigh_names = ("prev", "current", "next")
        return NeighHandle()

    def use_cyclic_boundaries_handler(self):
        self.border = SimpleBorderCopier()

    def use_constant_boundaries_handler(self, constant=0):
        assert constant == 0
        self.border = BorderSizeEnsurer()

    def set_extent(self, size):
        self.size = [size]

    def make_neigh(self, baseclass=None):
        assert self.neighbourhood, "call use_*_neighbourhood on the grid first!"
        assert len(self.neigh_names) > 0, "call *_names on the neighbourhood first!"
        if self.neighbourhood == "von_neumann":
            cls = ElementaryFlatNeighbourhood
        else:
            raise "Unimplemented neighbourhood " + self.neighbourhood
        if baseclass:
            self.neigh = cls(baseclass)
        else:
            self.neigh = cls()
        self.neigh.names = self.neigh_names

class Domain(object):
    def values(self):
        """Return a list of possible values"""
        return []
    def accepts(self, other):
        """Is the given value in the domain?"""
        return False

class RangeDomain(Domain):
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def values(self):
        return range(self.start, self.end)

    def accepts(self, other):
        return self.start <= other <= self.end

class ValuesDomain(Domain):
    def __init__(self, *values):
        self.vals = values

    def values(self): return self.vals[:]
    def accepts(self, other): return other in self.vals

class CellDescriptor(object):
    """Gives a nice API to set different cell's attributes on a State instance"""
    def __init__(self, state, cellname):
        self.state = state
        self.name = cellname

    def dtype(self, dtype):
        self.state.types[self.name] = dtype
        return self

    def default(self, value):
        self.state.defaults[self.name] = value
        return self

    def domain(self, domain):
        if isinstance(domain, tuple) and len(domain) == 2:
            self.state.domain[self.name] = RangeDomain(*domain)
        else:
            self.state.domain[self.name] = ValuesDomain(*domain)
        return self

class InteractivePalette(dict):
    def __init__(self, provider):
        super(InteractivePalette, self).__init__()
        self.provider = provider

    def __missing__(self, key):
        return self.provider(key)

class DisplayDef(object):
    pass

class AnsiDisplayDef(DisplayDef):
    """A display definition that supports characters, colors and a few
    terminal attributes like bold, inverted or underlined - depending on
    the terminal in use."""

    rendertype = ""
    """The kind of rendering to do

    - boxes
        Align all or some of the subcells in a big box.
        the "renderers" attribute is a dictionary that prescribes a rendering
        method for each subcell. Those are then composed into boxes using the
        inner_border and outer_border specifications.

    - box
        A custom function is used to generate one string representation of a
        whole cell and that is then wrapped into a box, if outer_border is
        set.
        This function is stored in the renderer attribute.
    """

    # TODO there should be a way to create boxes that derive from multiple subcells

    _sets = None
    _boxes = None
    borders = None
    renderer = None
    renderers = None
    col_widths = None
    row_heights = None
    cellspan_def = None

    def __init__(self, state, name):
        self.state = state
        self.name = name

        self._sets = None
        self._boxes = None
        self.renderers = {}

    def border(self, subcell, cell):
        self.borders = (subcell, cell)
        return self

    def boxes(self, **boxes):
        """Set the positioning of the subcells, if boxes are to be used."""
        self.rendertype = "boxes"
        fixed_boxes = {}
        fixed_sets = {}
        for k, v in boxes.iteritems():
            fixed_boxes[v] = k
            fixed_sets[v] = self.state.domain[k].values()
        self._boxes = fixed_boxes
        self._sets = fixed_sets
        return self

    def span_box(self, cell, width=1, height=1):
        """Define a box to span columns or rows"""
        assert (width != 1) != (height != 1), "can only rowspan or colspan" # XXX arbitrary restriction ...
        cellspan_def[cell] = (width, height)
        return self

    def numbers(self, *subcells):
        """Specify that numbers are to be used to render a subcell's contents"""
        for sc in subcells:
            self.renderers[sc] = ("numbers",) # XXX create a class or something for these?
        return self

    def palette(self, **subcell_palettes):
        """Takes a named argument for each subcell that provides a list or
        dictionary mapping subcell values to display characters"""
        for cell, scp in subcell_palettes.iteritems():
            self.renderers[cell] = ("palette", scp)
        return self

    def palettize_cell(self, fun):
        self.rendertype = "box"
        self.renderer = fun
        return fun

    def palettize_subcell(self, subcell):
        def subcell_palletizer_wrapper(fun):
            self.renderers[subcell] = ("function", fun)
            return fun
        return subcell_palletizer_wrapper

class State(object):
    names = None
    """The names of the state's subcells"""

    types = None
    """A mapping of name to type"""

    defaults = None
    """A mapping of name to default value"""

    domain = None
    """A mapping of name to what values are possible.

    Optional."""

    displays = None
    """A mapping of name to definition"""

    subcell = False

    def __init__(self):
        self.names = []
        self.types = {}
        self.defaults = {}
        self.domain = {}
        self.displays = {}

    def cell(self, name):
        self.names.append(name)
        if not self.subcell and len(self.names) > 1:
            self.subcell = True
        return CellDescriptor(self, name)

    def __getattr__(self, attr):
        if attr.startswith("display_"):
            clsname = (attr[len("display_"):]).title() + "DisplayDef"
            if clsname in globals():
                def make_the_display_class(name):
                    instance = globals()[clsname](self, name)
                    self.displays[name] = instance
                    return instance
                return make_the_display_class
            else:
                raise AttributeError()
        else:
            raise AttributeError()

class DoubleBufferStorage(object):
    state = None

    def __init__(self, grid, state, buffer_names=('cur', 'new')):
        self.state = state
        if state.subcell:
            print "using a subcell accessor"
            grid.acc = SubcellAccessor(state.names)
            grid.make_neigh(SubcellNeighbourhood)
        else:
            grid.acc = SimpleStateAccessor()
            grid.make_neigh()

class SubcellSimulator(CagenSimulator):
    sets = []
    def __init__(self, sim, sets, **kwargs):
        self.sets = sets
        super(SubcellSimulator, self).__init__(sim)

    def get_config(self):
        res = {}
        for k in self.sets:
            res[k] = getattr(self.t, "cconf_%s" % k)
        return res

class ZA(object):
    def __init__(self, grid, mem, code, base=2, extra_list=()):
        if isinstance(code, basestring):
            code = PasteComputation(py_code = code)

        self.size = grid.size
        self.mem = mem
        if self.mem.state.subcell:
            target = SubcellTarget(cells=self.mem.state.names, size=self.size, base=base)
        else:
            target = Target(self.size, None, base=base)
        stepfunc = StepFunc(
                loop=grid.loop,
                accessor=grid.acc,
                neighbourhood=grid.neigh,
                border=grid.border,
                visitors=[code] + list(extra_list),
                target=target)
        self.stepfunc = stepfunc
        self.stepfunc.gen_code()
        self.disp = {}
        self.sim = SubcellSimulator(stepfunc, self.mem.state.names)

    def display(self, display_to_use):
        assert isinstance(self.size, list) or len(self.size) == 1
        displaydef = self.mem.state.displays[display_to_use]

        if isinstance(displaydef, AnsiDisplayDef):
            if displaydef.rendertype == "boxes":
                palettes = {}
                for box, render in displaydef.renderers.iteritems():
                    if render[0] == "palette":
                        palettes[box] = render[1]
                    elif render[0] == "numbers":
                        pass
                    elif render[0] == "function":
                        raise NotImplementedError("function renderers not yet implemented")
            self.disp[display_to_use] = SubcellConsoleDisplay(self.sim, displaydef._boxes, displaydef._sets, palettes)
        else:
            raise NotImplementedError("Only AnsiDisplayDef implemented so far")

        #if self.mem.state.subcell:
            #class SubcellOneDimConsolePainter(SubcellPainterMixin, OneDimConsolePainter):
                #pass
        #self.disp = SubcellOneDimConsolePainter(self.sim, 1)

    def compile_py(self):
        pass

    def run(self, steps):
        for i in range(steps):
            self.sim.step_pure_py()
