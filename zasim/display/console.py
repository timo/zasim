from __future__ import absolute_import

from ..simulator import QObject

NO_DATA = " "
PALETTE =       [" ", "#", "-", ";", ",", "^", "+", "Y"]
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
        newline = "".join(self.palette[int(value)] for value in self._last_conf)
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
