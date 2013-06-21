from zasim.cagen import *
from zasim.simulator import *

class Grid(object):
    pass

class Grid1DEuclidean(Grid):
    neigh = None
    border = None
    acc = None
    loop = None
    size = []

    def __init__(self):
        self.loop = OneDimCellLoop()

    def use_von_neumann_neighbourhood(self, radius=1):
        assert radius == 1
        self.neigh = ElementaryFlatNeighbourhood()
        class NeighHandle(object):
            def __init__(self, neigh):
                self.neigh = neigh
            def compass_names(self):
                self.neigh.names = ("w", "e")
            def direction_names(self):
                self.neigh.names = ("left", "right")
            def ordering_names(self):
                self.neigh.names = ("prev", "next")
        return NeighHandle(self.neigh)

    def use_cyclic_boundaries_handler(self):
        self.border = SimpleBorderCopier()

    def use_constant_boundaries_handler(self, constant=0):
        assert constant == 0
        self.border = BorderSizeEnsurer()

    def set_extent(self, size):
        self.size = [size]

class DoubleBufferStorage(object):
    def __init__(self, grid, state, buffer_names=('cur', 'new')):
        grid.acc = SimpleStateAccessor()

class ZA(object):
    def __init__(self, grid, mem, nbh, code, extra_list=()):
        if isinstance(code, basestring):
            code = PasteComputation(py_code = code)
        size = grid.size
        target = target_class(size, None)
        size = target.size
        stepfunc = StepFunc(
                loop=grid.loop,
                accessor=grid.acc,
                neighbourhood=nbh,
                border=grid.border,
                visitors=[code] + extra_list,
                target=target)
        self.stepfunc = stepfunc
        self.stepfunc.gen_code()
        self.sim = CagenSimulator(stepfunc)

    def compile_py(self):
        pass

    def run(self, steps):
        for i in range(steps):
            self.sim.step()
