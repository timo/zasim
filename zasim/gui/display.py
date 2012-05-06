from __future__ import absolute_import

"""This module offers a display and interaction frontend with Qt.

It will try importing PySide first, and if that fails PyQt. The code will
constantly be tested with both bindings."""

from .displaywidgets import DisplayWidget, NewDisplayWidget
from .control import ControlWidget
#from .mainwin import ZasimMainWindow
display_objects = []

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
            if 'tiles' in self.simulator.palette_info:
                self.display = NewDisplayWidget(self.simulator)
            else:
                self.display = DisplayWidget(self.simulator)

        if self.control is None:
            self.control = ControlWidget(self.simulator)

        from .mainwin import ZasimMainWindow
        self.window = ZasimMainWindow(self.simulator, self.display, self.control)

        display_objects.append(self.window)
        self.window.show()

    def set_scale(self, scale):
        """Sets the scale of the display component."""
        self.display.set_scale(scale)

