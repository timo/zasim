# -*- coding: utf8 -*-
from __future__ import absolute_import

from ..simulator import QObject
import unicodedata
import itertools

import numpy as np

def n2c(name):
    """Turn a name of a subcell into x/y coords"""
    return int(name[1:name.find("l")]), int(name[name.find("l")+1:])

def c2n(x, y):
    return "c%dl%d" % (x, y)

NO_DATA = " "
PALETTE = [" "] + "░ ▒ ▓ █ ▇ ▆ ▅ ▄ ▃ ▂ ▁".split(" ")
#PALETTE = "▁ ▂ ▃ ▄ ▅ ▆ ▇ █".split(" ")
#PALETTE =       [" ", "#", "-", ";", ",", "^", "+", "Y"]
HTML_PALETTE = "#000 #fff #f00 #00f #0f0 #ff0 #0ff #f0f".split(" ")
PALETTE = dict(enumerate(PALETTE))
HTML_PALETTE = dict(enumerate(HTML_PALETTE))

class BaseConsolePainter(QObject):
    """This is a base class for implementing renderers that output the
    configuration of a simulator as an ascii-art string."""


    def __init__(self, simulator, extra=None, connect=True, auto_output=True, **kwargs):
        """Initialise the painter.

        :param simulator: The simulator to use.
        :param connect: Connect the signals of the simulator immediately?
        :param auto_output: Automatically output after every step?
        """
        super(BaseConsolePainter, self).__init__(**kwargs)
        self._sim = simulator
        self._data = []
        self._last_conf = None
        self._auto_output = auto_output

        if 'chars' in self._sim.palette_info:
            self.palette = self._sim.palette_info['chars']
        else:
            self.palette = PALETTE
            self._sim.palette_info['chars'] = self.palette

        if 'hexcols' in self._sim.palette_info:
            self.html_palette = self._sim.palette_info['hexcols']
        else:
            self.html_palette = HTML_PALETTE
            self._sim.palette_info['hexcols'] = self.html_palette

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

    def __str__(self):
        return "\n".join(self._data + [""])

    def _repr_html_(self):
        """IPython in version 0.11 and newer allows to display objects as html
        or png. This function turns the config into a html table."""
        value = """\
    <table style="border:0px;">
      %s
    </table>"""
        def line_to_html(data):
            reverse = lambda val: [k for k, v in self.palette.iteritems() if v == val][0]
            return ('<tr><td style="width: 10px; height: 10px; background: ' +
                    '">&nbsp;</td><td style="width: 10px; height: 10px; background: '.join(self.html_palette[reverse(value)] for value in data) +
                    '">&nbsp;</td></tr>')

        content = "\n".join(line_to_html(line) for line in self._data)

        return value % content

class SubcellPainterMixin(object):
    """Mixing this class into a BaseConsolePainter will override the
    `after_step` method with one that can handle subcell configs (barely)"""

    def after_step(self, update_step=True):
        confs = self._sim.get_config()
        keys = confs.keys()
        assert len(confs[keys[0]].shape) == 1
        newconfs = np.zeros((confs[keys[0]].size * len(keys)), dtype=confs[keys[0]].dtype)
        for i, k in enumerate(keys):
            newconfs[i::len(keys)] = confs[k]

        self._last_conf = newconfs

        self.draw_conf(update_step)
        if self._auto_output:
            print str(self),

class OneDimConsolePainter(BaseConsolePainter):
    """This painter draws the configs as they happen, newer configs pushing
    older configs out through the top."""

    def __init__(self, simulator, lines, **kwargs):
        super(OneDimConsolePainter, self).__init__(simulator, **kwargs)

        self._lines = lines
        self._data = [NO_DATA * self._sim.shape[0]]

        self.after_step()

    def draw_conf(self, update_step=True):
        # FIXME: numpypy int32 won't hash to the same as pythons int.
        newline = "".join(self.palette.get(int(value), "X") for value in self._last_conf)
        if len(self._data) == self._lines and update_step:
            self._data.pop(0)
        elif not update_step:
            self._data.pop(-1)
        self._data.append(newline)

    def export(self, filename):
        with open(filename, "w") as out:
            out.write("\n".join(self._data + [""]))

    def conf_replaced(self):
        self._data = [NO_DATA * self._sim.shape[0]]

class TwoDimConsolePainter(BaseConsolePainter):
    """This painter always draws the most current config."""

    def __init__(self, simulator, **kwargs):
        super(TwoDimConsolePainter, self).__init__(simulator, **kwargs)

        self._data = [[NO_DATA * self._sim.shape[1]]
                      for i in range(self._sim.shape[0])]

        self.after_step()

    def draw_conf(self, update_step=True):
        self._data = []
        for line in self._last_conf.T:
            # FIXME: numpypy int32 won't hash to the same as pythons int.
            newline = "".join(self.palette[int(value)] for value in line)
            self._data.append(newline)

    def __str__(self):
        return "\n".join(self._data + [""])

    def export(self, filename):
        with open(filename, "w") as out:
            out.write("\n".join(self._data + [""]))

class MultilineOneDimConsolePainter(BaseConsolePainter):
    """A painter for multiline palettes (as described in `convert_palette`)."""
    def __init__(self, simulator, compact_boxes=None, **kwargs):
        """:param simulator: The simulator to get configs from.
        :param compact_boxes: If this parameter is True, boxart palettes will
                              share borders for a more compact display."""

        super(MultilineOneDimConsolePainter, self).__init__(simulator, **kwargs)

        if 'cboxes' not in self._sim.palette_info:
            box_contents = map(str, simulator.t.possible_values)
            palette = self.convert_palette(self.box_art_palette([box_contents]))
            if compact_boxes is None:
                compact_boxes = True
            self._sim.palette_info['cboxes'] = palette
        else:
            palette = self._sim.palette_info['cboxes']

        self.palette = palette
        self.palette_height = len(palette.values()[0])

        self.compact_boxes = compact_boxes

    def draw_conf(self, update_step=True):
        self._data = [[] for _ in range(self.palette_height)]

        for cell in self._last_conf:
            aa_image = self.palette[cell]
            for line, data in enumerate(aa_image):
                try:
                    # if the last char of the previous bit matches up with the
                    # first char of the nex bit, remove one.
                    if self.compact_boxes and self._data[line][-1][-1] == data[0]:
                        data = data[1:]
                except IndexError:
                    pass
                self._data[line].append(data)

        # compose the bits inside each line to a full line, append a newline.
        self._data = ["".join(parts) for parts in self._data]

    @staticmethod
    def convert_palette(palette, values=None):
        """Convert a palette from the more easy to write format, where all first,
        second, third, ... lines share the same entry in an outer list, into the
        internal format, where each value is mapped to a list of lines."""

        result = {}

        num_rows = len(palette)
        num_entries = len(palette[0])
        if values is None:
            values = range(num_entries)

        for index, value in enumerate(values):
            result[value] = [palette[row_number][index] for row_number in xrange(num_rows)]

        return result

    @staticmethod
    def box_art_palette(palette, separate_lines=True, min_boxwidth=2):
        """Create boxes around each entry in the palette. If `separate_lines`
        is set, divide boxes vertically into separate parts.
        If `min_boxwidth` is set, boxes have a minimum width."""

        num_rows = len(palette)
        num_entries = len(palette[0])
        cell_width = min_boxwidth

        for index in range(num_entries):
            cell_width = max(
                             max(len(palette[row][index]) for row in xrange(num_rows)),
                             cell_width)

        upper_lower_rows = []
        separator_rows = []
        for index in xrange(num_entries):
            upper_lower_rows.append("+" + "=" * cell_width + "+")
            separator_rows.append("+" + "-" * cell_width + "+")

        new_palette = []
        for row_number, row in enumerate(palette):
            line = []
            for entry_number, entry in enumerate(row):
                line.append("|%s|" % (entry.center(cell_width)))
            new_palette.append(line)
            if separate_lines and row_number < len(palette) - 1:
                new_palette.append(separator_rows)

        return [upper_lower_rows] + new_palette + [upper_lower_rows]

# TODO write mixins that add border copying to the configs prior to drawing

def draw_box_template(boxes, t_w=1, w=None, h=None):
    """
    Create an ascii art template suitable for string interpolation.

    If you want correct outer borders, you need to wrap box positions for
    y=-1, y=h+1, x=-1 and x=w+1.

    :param boxes: a dictionary of x, y tuples mapped to strings that show what
                  subcells exist in the box and what they are called.
                  Alternatively, a list may be passed, in which case the names
                  will be created using the zacformat c2n function.
    :param t_w: the width of each of the columns. (may be a number, list or dict)
    :param w: How many subcells the box is wide
    :param h: How many subcells the box is tall
    :returns: a list of strings usable for drawing an ascii box art."""

    if isinstance(boxes, list):
        # use the c2n function to create the names for the positions
        boxes = dict(map(lambda position: (position, c2n(position)), boxes))

    if w is None:
        w = max([t[0] for t in boxes.keys()])
    if h is None:
        h = max([t[1] for t in boxes.keys()])

    if isinstance(t_w, int):
        t_w = [t_w for _ in range(w+1)]
    print "t_w is: ", t_w

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
                template[tpos] += corner(x, y) + up_h * (t_w[x] + 2)
                template[tpos + 1] += left_v + "%%(%s) %ds " % (boxes[(x, y)], t_w[x] + 1)
            else:
                if (x, y-1) in boxes or (x - 1, y) in boxes or (x-1,y-1) in boxes:
                    template[tpos] += corner(x, y)
                else:
                    template[tpos] += " "
                if (x, y-1) in boxes:
                    template[tpos] += up_h * (t_w[x] + 2)
                else:
                    template[tpos] += "  " + " " * t_w[x]
                if (x-1,y) in boxes:
                    template[tpos + 1] += left_v
                else:
                    template[tpos + 1] += " "
                if (x, y-1) not in boxes:
                    template[tpos + 1] += " "
                template[tpos + 1] += "  " + " " * t_w[x]

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
            template[tpos] += bhd * (t_w[x] + 2)
        else:
            template[tpos] += "  " + " " * t_w[x]

    if (w, h) in boxes:
        template[h * 2 + 2] += corner(w+1,h+1)

    return map(unicode, template)

def draw_tiled_box_template(boxes, w=1, twodim=True):
    """This makes template chunks for either four corners, four sides and a
    center for a lattice of box-templates or - if twodim is False - for the
    left and right end and the body of a line of box-templates."""

    if isinstance(boxes, list):
        # use the c2n function to create the names for the positions
        boxes = dict(map(lambda position: (position, c2n(position)), boxes))

    originalboxes = boxes.copy()

    if twodim:
        neighbours = itertools.product([-1,0,1], [-1,0,1])
    else:
        neighbours = itertools.product([-1,0,1], [0])

    content_width = w

    w = max([t[0] for t in originalboxes.keys()])
    h = max([t[1] for t in originalboxes.keys()])

    def d(x, y):
        return ((x, y), c2n(x, y))

    # determine wether the corners have boxes next to them.
    luc = d( -1, -1) if (w,h) in originalboxes.keys() else []
    ruc = d(w+1, -1) if (0,h) in originalboxes.keys() else []
    ldc = d( -1,h+1) if (w,0) in originalboxes.keys() else []
    rdc = d(w+1,h+1) if (0,0) in originalboxes.keys() else []

    def warp(src,dst,axis):
        res = []
        for box in originalboxes.keys():
            if box[axis] == src:
                if axis == 0:
                    res.append(d(dst, box[1]))
                else:
                    res.append(d(box[0], dst))
        return res

    # copy border boxes around
    lb = warp(0, w+1, 0)
    rb = warp(w,  -1, 0)

    ub = warp(h,  -1, 1)
    db = warp(0, h+1, 1)

    result_template = {}
    neighbours = list(neighbours)
    for x, y in neighbours:
        fixed = originalboxes.copy()
        if (x-1, y-1) in neighbours: fixed.update(ldc)
        if (x+1, y-1) in neighbours: fixed.update(rdc)
        if (x-1, y+1) in neighbours: fixed.update(luc)
        if (x+1, y+1) in neighbours: fixed.update(ruc)

        if (x+1, y  ) in neighbours: fixed.update(lb)
        if (x-1, y  ) in neighbours: fixed.update(rb)
        if (x,   y+1) in neighbours: fixed.update(ub)
        if (x,   y-1) in neighbours: fixed.update(db)

        result_template[(x,y)] = draw_box_template(fixed, content_width, w, h)

    return result_template

class SubcellConsoleDisplay(object):
    def __init__(self, simulator, boxes, sets, palettes, connect=True, auto_output=True):
        """Create a console displayer for showing cells that are made up of
        multiple subcells.

        :param boxes: A dictionary of a 2-tuple (the position)
                      to a string (the name) for each subcell.
                      Alternatively, a list may be passed, in which case the
                      names will be generated with zacformat.n2c.
        :param sets: A dictionary of name to a list of allowed (integer) values
        :param palettes: A dictionary of a name to a dictionary or list
                         of strings to be used for displaying.
        """
        self._sim = simulator
        self._data = []
        self._last_conf = None
        self._auto_output = auto_output

        if isinstance(boxes, list):
            # use the n2c function to create the names for the positions
            boxes = dict(map(lambda position: (n2c(position), position), boxes))

        self.boxes = boxes
        self.sets = sets
        self.palettes = palettes

        self._name_to_pos = {v:k for k, v in self.boxes.iteritems()}

        self.data = ""

        self.create_template()

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

    def create_template(self):
        max_w = {}
        for k, value in self.palettes.iteritems():
            x, y = self._name_to_pos[k]
            if isinstance(value, dict):
                max_w[x] = max(map(len, value.values()) + [max_w.get(x, 1)])
            else:
                max_w[x] = max(map(len, value) + [max_w.get(x, 1)])

        for k, vals in self.sets.iteritems():
            x, y = k
            if self.boxes[k] not in self.palettes:
                max_w[x] = max(map(len, map(str, vals)) + [max_w.get(x, 1)])

        #self.stringy_subcells = [k for k, v in self.sets.iteritems() if isinstance(v[0], basestring)]

        if len(self._sim.shape) == 1 or self._sim.shape[1] == 1:
            self.template = draw_tiled_box_template(self.boxes, max_w, twodim=False)
        else:
            self.template = draw_tiled_box_template(self.boxes, max_w)
        self.template_h = len(self.template[(0,0)])

    def draw_conf(self, update_step=True):
        size = self._last_conf.values()[0].shape
        if len(size) == 1:
            size = (size[0], 1)
        w, h = size
        def subpos(x, y):
            """Are we in a corner, at an edge or in the middle?"""
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
                    if k in self.palettes:
                        if h == 1:
                            val[k] = self.palettes[k][self._last_conf[k][x]]
                        else:
                            val[k] = self.palettes[k][self._last_conf[k][x,y]]
                    else:
                        if h == 1:
                            val[k] = self._last_conf[k][x]
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

