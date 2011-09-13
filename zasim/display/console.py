from __future__ import absolute_import

from ..simulator import QObject

class BaseConsolePainter(QObject):
    """This is a base class for implementing renderers that output the
    configuration of a simulator as an ascii-art string."""

    NO_DATA = " "
    PALETTE = [" ", "#", "-", ";"]

    def __init__(self, simulator, extra=None):
        """Initialise the painter.

        :param simulator: The simulator to use.
        """
        self._sim = simulator
        self._data = []
        self._last_conf = None

    def after_step(self, update_step=True):
        self._last_conf = self._sim.get_config().copy()
        self.draw_conf()

class LinearConsolePainter(BaseConsolePainter):
    NO_DATA = " "
    PALETTE = [" ", "#", "-", ";"]
    def __init__(self, simulator, lines):
        super(LinearConsolePainter, self).__init__(simulator)

        self._lines = lines
        self._data = [self.NO_DATA * self._sim.shape[0]]

    def draw_conf(self):
        newline = "".join(self.PALETTE[value] for value in self._last_conf)
        if len(self._data) == self._lines:
            self._data.pop(0)
        self._data.append(newline)

    def __str__(self):
        return "\n".join(self._data + [""])

    def export(self, filename):
        with open(filename, "w") as out:
            out.write("\n".join(self._data + [""]))

class TwoDimConsolePainter(BaseConsolePainter):
    def __init__(self, simulator, lines):
        super(LinearConsolePainter, self).__init__(simulator)

        self._data = [[self.NO_DATA * self._sim.shape[0]]
                      for i in range(self._sim.shape[1])]

    def draw_conf(self):
        self._data = []
        for line in self._last_conf:
            newline = "".join(self.PALETTE[value] for value in line)
            self._data.append(newline)

    def __str__(self):
        return "\n".join(self._data + [""])

    def export(self, filename):
        with open(filename, "w") as out:
            out.write("\n".join(self._data + [""]))

