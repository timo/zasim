"""This module implements whatever's necessary to work with .zac files
like text_to_cell outputs."""

import yaml
from .simulator import SimulatorInterface
from .cagen.neighbourhoods import SubcellNeighbourhood
from .cagen.accessors import SubcellAccessor
from .cagen.computations import PasteComputation
from .cagen.loops import OneDimCellLoop, TwoDimCellLoop
from .cagen.border import BorderSizeEnsurer
from .cagen.stepfunc import StepFunc
from .display.console import SubcellConsoleDisplay

import numpy as np

# due to circular import dependencies, these two functions are reproduced in
# display.console; don't edit them here, but not there!
def n2c(name):
    """Turn a name of a subcell into x/y coords"""
    return int(name[1:name.find("l")]), int(name[name.find("l")+1:])

def c2n(x, y):
    return "c%dl%d" % (x, y)

class ZacConsoleDisplay(SubcellConsoleDisplay):
    def __init__(self, simulator, connect=True, auto_output=True):
        boxes = simulator.sets.keys()
        palettes = {}
        for pos, values in simulator.sets.iteritems():
            if isinstance(values[0], basestring):
                palette = {}
                for value in values:
                    palette[simulator.strings.index(value)] = value
                palettes[pos] = palette
        super(ZacConsoleDisplay, self).__init__(simulator, boxes, palettes, connect=connect, auto_output=auto_output)

class ZacNeighbourhood(SubcellNeighbourhood):
    def __init__(self, neigh_data):
        names = []
        offsets = []
        for entry in neigh_data:
            names.append(entry["name"])
            offsets.append((entry["x"], entry["y"]))
        super(ZacNeighbourhood, self).__init__(names, offsets)

class ZacSimulator(SimulatorInterface):
    def __init__(self, data_or_file, shape):
        super(ZacSimulator, self).__init__()
        if isinstance(data_or_file, file):
            data = yaml.load(data_or_file)
        else:
            data = yaml.loads(data_or_file)

        self.sets = data["sets"]
        self.cells = self.sets.keys()
        self.strings = data["strings"]
        self.python_code = "# auto-generated code:\n" + data["python_code"]
        self.cpp_code = data["cpp_code"]
        if len(shape) == 1:
            shape = (shape[0], 1)
        self.shape = shape

        self.possible_values = self.sets

        self.stringy_subcells = [k for k, v in self.sets.iteritems() if isinstance(v[0], basestring)]

        self.neighbourhood = ZacNeighbourhood(data["neighbourhood"])
        self.acc = SubcellAccessor(self.sets.keys())
        self.computation = PasteComputation(self.cpp_code, self.python_code)
        self.border = BorderSizeEnsurer()

        if len(shape) == 1:
            self.loop = OneDimCellLoop()
        else:
            self.loop = TwoDimCellLoop()

        for k in self.sets.keys():
            nconf_arr = np.zeros(shape, dtype=int)
            cconf_arr = np.zeros(shape, dtype=int)
            setattr(self, "cconf_%s" % k, cconf_arr)
            setattr(self, "nconf_%s" % k, nconf_arr)
            if k in self.stringy_subcells:
                val = [index for index, val in enumerate(self.strings) if val == self.sets[k][0]][0]
                cconf_arr[:] = val
                nconf_arr[:] = val

        self.stepfunc = StepFunc(self, self.loop, self.acc, self.neighbourhood, self.border, visitors=[self.computation])
        self.stepfunc.gen_code()

    def get_config(self):
        res = {}
        for k in self.sets.keys():
            res[k] = getattr(self, "cconf_%s" % k)
        return res

    def step(self):
        self.stepfunc.step()
        self.updated.emit()

