"""This module implements whatever's necessary to work with .zac files
like text_to_cell outputs."""

import yaml
import unicodedata
import itertools

n2c = lambda name: (int(name[1:name.find("l")]), int(name[name.find("l")+1:]))
n2c.__doc__ = """Turn a name of a subcell into x/y coords"""
c2n = lambda x, y: "c%dl%d" % (x, y)

def draw_box_template(boxes, t_w=1):
    """
    Create an ascii art template suitable for string interpolation.

    If you want correct outer borders, you need to wrap box positions for
    y=-1, y=h+1, x=-1 and x=w+1.

    :param boxes: a list of x, y tuples that show which fields are filled.
    :param w: the width of each of the boxes.
    :returns: a list of strings usable for drawing an ascii box art."""

    w = max([t[0] for t in boxes])
    h = max([t[1] for t in boxes])

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

    neighbours = itertools.product([-1,0,1], [-1, 0, 1])

    content_width = w

    w = max([t[0] for t in boxes])
    h = max([t[1] for t in boxes])

    # determine wether the corners have boxes next to them.
    luc = [(-1,-1)] if (w,h) in boxes else []
    ruc = [( w,-1)] if (0,h) in boxes else []
    ldc = [(-1, h)] if (w,0) in boxes else []
    rdc = [( w, h)] if (0,0) in boxes else []

    def warp(src,dst,axis):
        res = []
        for box in boxes:
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
    for x, y in neighbours:
        fixed = originalboxes[:]
        if (x-1, y-1) in neighbours: fixed.extend(luc)
        if (x+1, y-1) in neighbours: fixed.extend(ruc)
        if (x-1, y+1) in neighbours: fixed.extend(ldc)
        if (x+1, y+1) in neighbours: fixed.extend(rdc)

        if (x-1, y  ) in neighbours: fixed.extend(lb)
        if (x+1, y  ) in neighbours: fixed.extend(rb)
        if (x,   y-1) in neighbours: fixed.extend(ub)
        if (x,   y+1) in neighbours: fixed.extend(db)

        result_template[(x,y)] = draw_box_template(fixed, content_width)

    return result_template

class ZacConsoleDisplay(object):
    def __init__(self, simulator, sets, strings, connect=True, auto_output=True):
        self._sim = simulator
        self._data = []
        self._last_conf = None
        self._auto_output = auto_output
        self.sets = sets
        self.strings = strings

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
            print str(self),

    def conf_changed(self):
        self.after_step(False)

    def conf_replaced(self):
        self.conf_changed()

    def measure_sets(self):
        all_contents = sum(self.sets.values(), [])
        max_w = max(map(len, all_contents))

        coords = map(n2c, self.sets.keys())

        self.template = draw_box_template(coords, max_w)

    def draw_conf(self, update_step=True):
        pass

class ZacSimulator(object):
    def __init__(self, data_or_file):
        if isinstance(data_or_file, file):
            data = yaml.load(data_or_file)
        else:
            data = yaml.loads(data_or_file)

        self.sets = data.sets
        self.strings = data.strings
        self.python_code = data.python_code
        self.cpp_code = data.cpp_code

