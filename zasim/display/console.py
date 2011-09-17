from __future__ import absolute_import

from ..simulator import QObject

class BaseConsolePainter(QObject):
    """This is a base class for implementing renderers that output the
    configuration of a simulator as an ascii-art string."""

    NO_DATA = " "
    PALETTE =       ["#", " ", "-", ";", ",", "^", "+", "Y"]
    HTML_PALETTE = "#000 #fff #f00 #00f #0f0 #ff0 #0ff #f0f".split(" ")

    def __init__(self, simulator, extra=None, connect=True, auto_output=True, **kwargs):
        """Initialise the painter.

        :param simulator: The simulator to use.
        """
        super(BaseConsolePainter, self).__init__(**kwargs)
        self._sim = simulator
        self._data = []
        self._last_conf = None
        self._auto_output = auto_output

        if connect:
            self.connect_simulator()

    def connect_simulator(self):
        self._sim.changed.connect(self.conf_changed)
        self._sim.updated.connect(self.after_step)

    def after_step(self, update_step=True):
        self._last_conf = self._sim.get_config().copy()
        self.draw_conf(update_step)
        if self._auto_output:
            print str(self),

    def conf_changed(self):
        self.after_step(False)

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
            return ('<tr><td style="width: 10px; height: 10px; background: ' +
                    '">&nbsp;</td><td style="width: 10px; height: 10px; background: '.join(self.HTML_PALETTE[self.PALETTE.index(value)] for value in data) +
                    '">&nbsp;</td></tr>')

        content = "\n".join(line_to_html(line) for line in self._data)

        return value % content

class LinearConsolePainter(BaseConsolePainter):
    """This painter draws the configs as they happen, newer configs pushing
    older configs out through the top."""

    def __init__(self, simulator, lines, **kwargs):
        super(LinearConsolePainter, self).__init__(simulator, **kwargs)

        self._lines = lines
        self._data = [self.NO_DATA * self._sim.shape[0]]

    def draw_conf(self, update_step=True):
        newline = "".join(self.PALETTE[value] for value in self._last_conf)
        if len(self._data) == self._lines and update_step:
            self._data.pop(0)
        self._data.append(newline)

    def export(self, filename):
        with open(filename, "w") as out:
            out.write("\n".join(self._data + [""]))


class TwoDimConsolePainter(BaseConsolePainter):
    """This painter always draws the most current config."""

    def __init__(self, simulator, **kwargs):
        super(TwoDimConsolePainter, self).__init__(simulator, **kwargs)

        self._data = [[self.NO_DATA * self._sim.shape[0]]
                      for i in range(self._sim.shape[1])]

    def draw_conf(self, update_step=True):
        self._data = []
        for line in self._last_conf:
            newline = "".join(self.PALETTE[value] for value in line)
            self._data.append(newline)

    def __str__(self):
        return "\n".join(self._data + [""])

    def export(self, filename):
        with open(filename, "w") as out:
            out.write("\n".join(self._data + [""]))

# TODO write mixins that add border copying to the configs prior to drawing
