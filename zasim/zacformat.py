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
from .display.console import draw_tiled_box_template

import numpy as np

n2c = lambda name: (int(name[1:name.find("l")]), int(name[name.find("l")+1:]))
n2c.__doc__ = """Turn a name of a subcell into x/y coords"""
c2n = lambda x, y: "c%dl%d" % (x, y)

class ZacConsoleDisplay(object):
    def __init__(self, simulator, connect=True, auto_output=True):
        self._sim = simulator
        self._data = []
        self._last_conf = None
        self._auto_output = auto_output
        self.sets = simulator.sets
        self.strings = simulator.strings

        self.data = ""

        self.measure_sets()

        if connect:
            self.connect_simulator()

    def connect_simulator(self):
        self._sim.changed.connect(self.conf_changed)
        self._sim.updated.connect(self.after_step)
        self._sim.snapshot_restored.connect(self.conf_replaced)

    def after_step(self, update_step=True):
        self._last_conf = self._sim.get_config().copy()
        self.draw_conf(update_step)
        if self._auto_output:
            print unicode(self)
            print

    def conf_changed(self):
        self.after_step(False)

    def conf_replaced(self):
        self.conf_changed()

    def measure_sets(self):
        all_contents = sum(self.sets.values(), [])
        max_w = max(map(len, map(unicode, all_contents)))

        self.stringy_subcells = [k for k, v in self.sets.iteritems() if isinstance(v[0], basestring)]

        coords = map(n2c, self.sets.keys())

        if len(self._sim.shape) == 1 or self._sim.shape[1] == 1:
            self.template = draw_tiled_box_template(coords, max_w, twodim=False)
        else:
            self.template = draw_tiled_box_template(coords, max_w)
        self.template_h = len(self.template[(0,0)])

    def draw_conf(self, update_step=True):
        size = self._last_conf.values()[0].shape
        if len(size) == 1:
            size = (size[0], 1)
        w, h = size
        def subpos(x, y):
            xp = -1 if x == 0 else ( 1 if x == w-1 else 0)
            yp =  1 if y == 0 else (-1 if y == h-1 else 0)
            if h == 1:
                yp = 0
            return (xp, yp)

        datalines = []
        for y in range(h):
            lines = [[] for _ in range(self.template_h)]
            for x in range(w):
                val = dict()
                for k in self._last_conf.keys():
                    if k in self.stringy_subcells:
                        val[k] = self.strings[self._last_conf[k][x,y]]
                    else:
                        val[k] = self._last_conf[k][x,y]
                sp   = subpos(x,y)
                box  = [line % val for line in self.template[sp]]
                for line in lines:
                    if len(line):
                        line[-1] = line[-1][:-1]
                [line.append(boxcontent) for line, boxcontent in zip(lines, box)]
            datalines = datalines[:-1]
            datalines.extend("".join(line_c) for line_c in lines)
        self.data = "\n".join(datalines)

    def __unicode__(self):
        try:
            return self.data
        except:
            return "error"

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

