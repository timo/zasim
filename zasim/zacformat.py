"""This module implements whatever's necessary to work with .zac files
like text_to_cell outputs."""

import yaml
import unicodedata
import itertools
from .simulator import SimulatorInterface
from .cagen.neighbourhoods import SimpleNeighbourhood
from .cagen.accessors import SubcellAccessor
from .cagen.computations import PasteComputation
from .cagen.loops import OneDimCellLoop, TwoDimCellLoop
from .cagen.utils import gen_offset_pos
from .cagen.stepfunc import StepFunc

import numpy as np

n2c = lambda name: (int(name[1:name.find("l")]), int(name[name.find("l")+1:]))
n2c.__doc__ = """Turn a name of a subcell into x/y coords"""
c2n = lambda x, y: "c%dl%d" % (x, y)

def draw_box_template(boxes, t_w=1, w=None, h=None):
    """
    Create an ascii art template suitable for string interpolation.

    If you want correct outer borders, you need to wrap box positions for
    y=-1, y=h+1, x=-1 and x=w+1.

    :param boxes: a list of x, y tuples that show which fields are filled.
    :param w: the width of each of the boxes.
    :returns: a list of strings usable for drawing an ascii box art."""

    w = w or max([t[0] for t in boxes])
    h = h or max([t[1] for t in boxes])

    def corner(x, y):
        a = (x-1, y-1) in boxes
        b = (x,   y-1) in boxes
        c = (x-1, y)   in boxes
        d = (x,y)      in boxes

        if not a and not b and not c and not d:
            return " "

        # which lines should be drawn double?
        ld = x == 0 or x == w + 1
        ud = y == 0 or y == h + 1
        if ld == ud:
            both = "DOUBLE " if ld else "LIGHT "
        else:
            both = None

        # the unicode name
        n = "BOX DRAWINGS "

        if both:
            n += both

        if c and b or a and d:
            if both:
                n += "VERTICAL AND HORIZONTAL"
            elif ld:
                n += "VERTICAL DOUBLE AND HORIZONTAL SINGLE"
            elif ud:
                n += "VERTICAL SINGLE AND HORIZONTAL DOUBLE"

        elif b and d or a and c:
            n += "VERTICAL "
            if ld and not ud:
                n += "DOUBLE "
            elif ud and not ld:
                n += "SINGLE "
            if a:
                n += "AND LEFT "
            else:
                n += "AND RIGHT "
            if ld and not ud:
                n += "SINGLE"
            if ud and not ld:
                n += "DOUBLE"

        elif a and b or c and d:
            if a:
                n += "UP "
            else:
                n += "DOWN "
            if ld and not ud:
                n += "DOUBLE "
            elif not ld and ud:
                n += "SINGLE "
            n += "AND HORIZONTAL "
            if not ud and ld:
                n += "SINGLE"
            elif not ld and ud:
                n += "DOUBLE"

        else:
            if not c and not d:
                n += "UP "
            else:
                n += "DOWN "
            if ld and not both:
                n += "DOUBLE "
            if not ld and not both:
                n += "SINGLE "
            n += "AND "
            if not b and not d:
                n += "LEFT "
            else:
                n += "RIGHT "
            if ud and not both:
                n += "DOUBLE "
            elif not ud and not both:
                n += "SINGLE "

        try:
            res = unicodedata.lookup(n.rstrip())
        except:
            res = n.rstrip()
        # print x, y, a, b, c, d, ld, ud, res
        return res

    bhs, bhd = [unicodedata.lookup("BOX DRAWINGS %s HORIZONTAL" % a) for a in "LIGHT DOUBLE".split(" ")]
    bvs, bvd = [unicodedata.lookup("BOX DRAWINGS %s VERTICAL" % a) for a in "LIGHT DOUBLE".split(" ")]

    template = ["" for _ in range(h * 2 + 3)]
    for x in range(w+1):
        left_v = bvs if x != 0 else bvd
        for y in range(h+1):
            tpos = y * 2
            up_h = bhs if y != 0 else bhd
            if (x, y) in boxes:
                template[tpos] += corner(x, y) + up_h * (t_w + 2)
                template[tpos + 1] += left_v + "%%(%s) %ds " % (c2n(x, y), t_w + 1)
            else:
                if (x, y-1) in boxes or (x - 1, y) in boxes or (x-1,y-1) in boxes:
                    template[tpos] += corner(x, y)
                else:
                    template[tpos] += " "
                if (x, y-1) in boxes:
                    template[tpos] += up_h * (t_w + 2)
                else:
                    template[tpos] += "  " + " " * t_w
                if (x-1,y) in boxes:
                    template[tpos + 1] += left_v
                else:
                    template[tpos + 1] += " "
                template[tpos + 1] += "  " + " " * t_w

    for y in range(h+1):
        tpos = y * 2
        if (w,y) in boxes or (x, y-1) in boxes:
            template[tpos] += corner(w + 1, y)
        else:
            template[tpos] += " "
        if (w,y) in boxes:
            template[tpos + 1] += bvd

    for x in range(w+1):
        tpos = h * 2 + 2
        if (x, h) in boxes or (x-1,h) in boxes:
            template[tpos] += corner(x, h + 1)
        else:
            template[tpos] += " "
        if (x, h) in boxes:
            template[tpos] += bhd * (t_w + 2)
        else:
            template[tpos] += "  " + " " * t_w

    if (w, h) in boxes:
        template[h * 2 + 2] += corner(w+1,h+1)

    return template

def draw_tiled_box_template(boxes, w=1, twodim=True):
    """This makes template chunks for either four corners, four sides and a
    center for a lattice of box-templates or - if twodim is False - for the
    left and right end and the body of a line of box-templates."""

    originalboxes = boxes[:]

    if twodim:
        neighbours = itertools.product([-1,0,1], [-1,0,1])
    else:
        neighbours = itertools.product([-1,0,1], [0])

    content_width = w

    w = max([t[0] for t in originalboxes])
    h = max([t[1] for t in originalboxes])

    # determine wether the corners have boxes next to them.
    luc = [( -1, -1)] if (w,h) in originalboxes else []
    ruc = [(w+1, -1)] if (0,h) in originalboxes else []
    ldc = [( -1,h+1)] if (w,0) in originalboxes else []
    rdc = [(w+1,h+1)] if (0,0) in originalboxes else []

    def warp(src,dst,axis):
        res = []
        for box in originalboxes:
            if box[axis] == src:
                if axis == 0:
                    res.append((dst, box[1]))
                else:
                    res.append((box[0], dst))
        return res

    # copy border boxes around
    lb = warp(0, w+1, 0)
    rb = warp(w,  -1, 0)

    ub = warp(h,  -1, 1)
    db = warp(0, h+1, 1)

    result_template = {}
    neighbours = list(neighbours)
    for x, y in neighbours:
        fixed = originalboxes[:]
        if (x-1, y-1) in neighbours: fixed.extend(ldc); print "ldc"
        if (x+1, y-1) in neighbours: fixed.extend(rdc); print "rdc"
        if (x-1, y+1) in neighbours: fixed.extend(luc); print "luc"
        if (x+1, y+1) in neighbours: fixed.extend(ruc); print "ruc"

        if (x+1, y  ) in neighbours: fixed.extend(lb); print "lb"
        if (x-1, y  ) in neighbours: fixed.extend(rb); print "rb"
        if (x,   y+1) in neighbours: fixed.extend(ub); print "ub"
        if (x,   y-1) in neighbours: fixed.extend(db); print "db"

        result_template[(x,y)] = draw_box_template(fixed, content_width, w, h)

    return result_template

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
        max_w = max(map(len, map(str, all_contents)))

        self.stringy_subcells = [k for k, v in self.sets.iteritems() if isinstance(v[0], basestring)]

        coords = map(n2c, self.sets.keys())

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
                # TODO condense like in TwoDimConsolePainter
                [line.append(boxcontent) for line, boxcontent in zip(lines, box)]
            # TODO condense like in TwoDimConsolePainter
            datalines.extend("".join(line_c) for line_c in lines)
        self.data = "\n".join(datalines)

    def __unicode__(self):
        try:
            return self.data
        except:
            return "error"

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

        for subcell in self.subcells:
            assignments = ["%s_%s = self.acc.read_from(%s, %s)" % (
                            name, subcell, "offset_pos(pos, %s)" % (offset,), subcell)
                            for name, offset in zip(self.names, self.offsets)]
        self.code.add_py_code("pre_compute",
                "\n".join(assignments))

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

        self.possible_values = self.sets

        self.stringy_subcells = [k for k, v in self.sets.iteritems() if isinstance(v[0], basestring)]

        self.neighbourhood = ZacNeighbourhood(data["neighbourhood"], self.sets.keys())
        self.acc = SubcellAccessor(self.sets.keys())
        self.computation = PasteComputation(self.cpp_code, self.python_code)

        if len(shape) == 1:
            self.loop = OneDimCellLoop()
        else:
            self.loop = TwoDimCellLoop()

        self.cconf = {}
        self.nconf = {}
        for k in self.sets.keys():
            self.cconf[k] = np.zeros(shape, dtype=int)
            self.nconf[k] = np.zeros(shape, dtype=int)
            if k in self.stringy_subcells:
                val = [index for index, val in enumerate(self.strings) if val == self.sets[k][0]][0]
                self.cconf[k][:] = val
                self.nconf[k][:] = val

        self.stepfunc = StepFunc(self, self.loop, self.acc, self.neighbourhood, extra_code=[self.computation])
        self.stepfunc.gen_code()

    def get_config(self):
        return self.cconf

