from __future__ import absolute_import

"""This module offers a display and interaction frontend with Qt.

It will try importing PySide first, and if that fails PyQt. The code will
constantly be tested with both bindings."""

from .displaywidgets import NewDisplayWidget
from .control import ControlWidget
from .mainwin import ZasimMainWindow
display_objects = []

from zasim.cagen.jvn import PALETTE_JVN_IMAGE, PALETTE_JVN_RECT

class ZasimDisplay(object):

    simulator = None
    """The `Simulator` object for this display."""

    display = None
    """The `BaseDisplayWidget` in use."""

    window = None
    """The `ZasimMainWindow` instance in use."""

    control = None
    """The `ControlWidget` in use."""

    def __init__(self, simulator):
        """Instantiate a Display (thas is: a window with a display widget and
        simulation controls) from a simulator.

        :param simulator: The simulator to use."""

        self.simulator = simulator

        if not self.display:
            self.display = NewDisplayWidget(self.simulator, PALETTE_JVN_IMAGE, PALETTE_JVN_RECT)

        if self.control is None:
            self.control = ControlWidget(self.simulator)

        if self.window is None:
            self.window = ZasimMainWindow(self.simulator, self.display, self.control)
        self.window.show()

    def set_scale(self, scale):
        """Sets the scale of the display component."""
        self.display.set_scale(scale)

