from __future__ import absolute_import

"""This module offers a display and interaction frontend with Qt.

It will try importing PySide first, and if that fails PyQt. The code will
constantly be tested with both bindings."""

from .displaywidgets import DisplayWidget
from .control import ControlWidget
from .mainwin import ZasimMainWindow
display_objects = []

class ZasimDisplay(object):

    simulator = None
    """The :class:`Simulator` object for this display."""

    display = None
    """The :class:`BaseDisplayWidget` in use."""

    window = None
    """The :class:`ZasimMainWindow` instance in use."""

    control = None
    """The :class:`ControlWidget` in use."""

    def __init__(self, simulator):
        """Instantiate a Display (thas is: a window with a display widget and
        simulation controls) from a simulator.

        :param simulator: The simulator to use."""

        self.simulator = simulator

        if not self.display:
            self.display = DisplayWidget(self.simulator)

        if self.control is None:
            self.control = ControlWidget(self.simulator)

        if self.window is None:
            self.window = ZasimMainWindow(self.simulator, self.display, self.control)
        self.window.show()

    def set_scale(self, scale):
        """Sets the scale of the display component."""
        self.display.set_scale(scale)

