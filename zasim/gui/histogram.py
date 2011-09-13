from ..external.qt import QColor, QPainter, QPoint, QLine
from .bases import BaseExtraDisplay
import Queue

class HistogramExtraDisplay(BaseExtraDisplay):
    """This extra display can take any attribute from the simulation target
    that is an one-dimensional array and display its values over time as
    colored vertical lines."""
    colors = [QColor("black"), QColor("white"), QColor("red"), QColor("blue"),
              QColor("green"), QColor("yellow")]
    def __init__(self, sim, attribute="histogram", width=400, maximum=1.0, **kwargs):
        super(HistogramExtraDisplay, self).__init__(title=attribute, sim=sim, width=width, **kwargs)
        self.linepos = 0
        self.queue = Queue.Queue(width)
        self.attribute = attribute
        self.update_no_step = False

    def paint_display_widget(self, event):
        painter = QPainter(self.image)
        linepos = self.linepos
        try:
            while True:
                values = self.queue.get_nowait()
                maximum = sum(values)
                scale = self.img_height * 1.0 / maximum
                absolute = 0.0
                for value, color in zip(values, self.colors):
                    value = value * scale
                    painter.setPen(color)
                    painter.drawLine(QLine(linepos, absolute,
                                     linepos, absolute + value))
                    absolute += value

                if not self.update_no_step:
                    linepos += 1
                    if linepos >= self.width():
                        linepos = 0

        except Queue.Empty:
            pass

        copier = QPainter(self.display_widget)
        copier.drawImage(QPoint(0, 0), self.image)
        del copier
        self.linepos = linepos

    def after_step(self):
        value = getattr(self.sim.t, self.attribute).copy()
        try:
            self.queue.put_nowait(value)
        except Queue.Full:
            self.queue.get()
            self.queue.put(value)

        self.update_no_step = False
        self.display_widget.update()

    def conf_changed(self):
        self.after_step()
        self.update_no_step = True

