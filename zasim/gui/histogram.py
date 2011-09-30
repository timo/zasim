from .bases import BaseExtraDisplay
from ..display.qt import HistogramPainter

class HistogramExtraDisplay(BaseExtraDisplay):
    """This extra display can take any attribute from the simulation target
    that is an one-dimensional array and display its values over time as
    colored vertical lines."""

    def __init__(self, sim, attribute="histogram", width=400, height=150, maximum=1.0, **kwargs):
        super(HistogramExtraDisplay, self).__init__(title=attribute, sim=sim, width=width, height=height, **kwargs)
        self.display = HistogramPainter(sim, attribute, width, height)

        self.display.setObjectName("display")
        self.display.update.connect(self.display_widget.update)

