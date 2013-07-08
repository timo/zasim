# -*- coding: utf8 -*-
from __future__ import absolute_import

from ..simulator import QObject
import unicodedata
import itertools

import numpy as np

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

    # TODO move boxes around manually, so that it doesn't only work with zacformat

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
        if (x-1, y-1) in neighbours: fixed.extend(ldc)
        if (x+1, y-1) in neighbours: fixed.extend(rdc)
        if (x-1, y+1) in neighbours: fixed.extend(luc)
        if (x+1, y+1) in neighbours: fixed.extend(ruc)

        if (x+1, y  ) in neighbours: fixed.extend(lb)
        if (x-1, y  ) in neighbours: fixed.extend(rb)
        if (x,   y+1) in neighbours: fixed.extend(ub)
        if (x,   y-1) in neighbours: fixed.extend(db)

        result_template[(x,y)] = draw_box_template(fixed, content_width, w, h)

    return result_template
