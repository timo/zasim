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

class DoubleBufferStorage(object):
    state = {}

    def __init__(self, grid, state, buffer_names=('cur', 'new')):
        self.state = state.copy()
        if len(state) == 1:
            grid.acc = SimpleStateAccessor()
            grid.make_neigh()
        else:
            print "using a subcell accessor"
            grid.acc = SubcellAccessor(state.keys())
            grid.make_neigh(SubcellNeighbourhood)

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
    def __init__(self, grid, mem, code, extra_list=()):
        if isinstance(code, basestring):
            code = PasteComputation(py_code = code)

        self.size = grid.size
        self.mem = mem
        if len(self.mem.state) > 1:
            target = SubcellTarget(cells=self.mem.state.keys(), size=self.size)
        else:
            target = Target(self.size, None)
        stepfunc = StepFunc(
                loop=grid.loop,
                accessor=grid.acc,
                neighbourhood=grid.neigh,
                border=grid.border,
                visitors=[code] + list(extra_list),
                target=target)
        self.stepfunc = stepfunc
        self.stepfunc.gen_code()
        self.sim = SubcellSimulator(stepfunc, self.mem.state.keys())

    def display(self):
        assert isinstance(self.size, list) or len(self.size) == 1
        if len(self.mem.state) > 1:
            class SubcellOneDimConsolePainter(SubcellPainterMixin, OneDimConsolePainter):
                pass
        self.disp = SubcellOneDimConsolePainter(self.sim, 1)

    def compile_py(self):
        pass

    def run(self, steps):
        for i in range(steps):
            self.sim.step()
