"""This module implements whatever's necessary to work with .zac files
like text_to_cell outputs."""

# This file is part of zasim. zasim is licensed under the BSD 3-clause license.
# See LICENSE.txt for details.

import yaml
from .simulator import SimulatorInterface
from .cagen.neighbourhoods import SimpleNeighbourhood
from .cagen.accessors import SubcellAccessor
from .cagen.computations import PasteComputation
from .cagen.loops import OneDimCellLoop, TwoDimCellLoop
from .cagen.utils import gen_offset_pos
from .cagen.border import BorderSizeEnsurer
from .cagen.stepfunc import StepFunc
from .cagen.target import SubCellTarget

class ZacNeighbourhood(SimpleNeighbourhood):
    def __init__(self, neigh_data, subcells):
        names = []
        offsets = []
        for entry in neigh_data:
            names.append(entry["name"])
            offsets.append((entry["x"], entry["y"]))
        super(ZacNeighbourhood, self).__init__(names, offsets)

        self.subcells = subcells

    def visit(self):
        """Adds C and python code to get the neighbouring values and stores
        them in local variables."""
        for name, offset in zip(self.names, self.offsets):
            for subcell in self.subcells:
                self.code.add_weave_code("pre_compute", "%s_%s = %s;" % (name, subcell,
                         self.code.acc.read_access(
                             gen_offset_pos(self.code.loop.get_pos(), offset), subcell)))

        for subcell in self.subcells:
            self.code.add_weave_code("localvars",
                    "int " + ", ".join(map(lambda n: "%s_%s" % (n, subcell), self.names)) + ";")

        assignments = []
        for subcell in self.subcells:
            assignments.extend(["%s_%s = self.acc.read_from(%s, '%s')" % (
                            name, subcell, "offset_pos(pos, %s)" % (offset,), subcell)
                            for name, offset in zip(self.names, self.offsets)])
        self.code.add_py_code("pre_compute",
                "\n".join(assignments))

class ZacSimulator(SimulatorInterface):
    def __init__(self, data_or_file, shape, configs={}):
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

        self.neighbourhood = ZacNeighbourhood(data["neighbourhood"], self.sets.keys())
        self.acc = SubcellAccessor(self.sets.keys())
        self.computation = PasteComputation(self.cpp_code, self.python_code)
        self.border = BorderSizeEnsurer()

        if len(shape) == 1:
            self.loop = OneDimCellLoop()
        else:
            self.loop = TwoDimCellLoop()

        self.target = SubCellTarget(self.sets, shape, self.strings, configs)

        self.stepfunc = StepFunc(self.target, self.loop, self.acc, self.neighbourhood, self.border, visitors=[self.computation])
        self.stepfunc.gen_code()

    def get_config(self):
        res = {}
        for k in self.sets.keys():
            res[k] = getattr(self, "cconf_%s" % k)
        return res

    def step(self):
        self.stepfunc.step()
        self.updated.emit()

