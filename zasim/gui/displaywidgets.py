from .bases import BaseDisplayWidget
from ..external.qt import QPainter, QImage, QPoint, QRect, QSize

import numpy as np
import Queue

class HistoryDisplayWidget(BaseDisplayWidget):
    """A Display that displays one-dimensional cellular automatons by drawing
    consecutive configurations below each other, wrapping around to the top."""
    def __init__(self, simulator, height, scale=1, **kwargs):
        """:param simulator: The simulator to use.
        :param height: The amount of lines of history to keep before wrapping.
        :param scale: The size of each pixel.
        :param parent: The QWidget to set as parent."""
        super(HistoryDisplayWidget, self).__init__(width=simulator.shape[0],
                      height=height,
                      queue_size=height,
                      scale=scale,
                      **kwargs)
        self.sim = simulator
        self.update_no_step = False

    def paintEvent(self, ev):
        """Get new configurations, update the internal pixmap, refresh the
        display.

        This is called from Qt whenever a repaint is in order. Do not call it
        yourself. :meth:`after_step` will call update, which will trigger a
        :meth:`paintEvent`.

        .. note::
            In order not to turn into an endless loop, update at most 100
            lines or :attr:`size` lines, whichever is lower."""
        rendered = 0
        y = self.last_step % self.img_height
        w = self.img_width
        scale = self.img_scale
        try:
            painter = QPainter(self.image)
            while rendered < min(100, self.img_height):
                conf = self.display_queue.get_nowait()
                nconf = np.empty((w, 1, 2), np.uint8, "C")
                if not self.invert_odd or self.odd:
                    nconf[...,0,0] = conf * 255
                else:
                    nconf[...,0,0] = (1 - conf) * 255
                nconf[...,1] = nconf[...,0]

                image = QImage(nconf.data, w, 1, QImage.Format_RGB444).scaled(w * scale, scale)
                painter.drawImage(QPoint(0, y * scale), image)

                self.queued_steps -= 1
                rendered += 1
                if not self.update_no_step:
                    self.last_step += 1
                    y = self.last_step % self.img_height
                    self.odd = not self.odd
                else:
                    self.update_no_step = False
        except Queue.Empty:
            pass

        copier = QPainter(self)
        copier.drawImage(QPoint(0, 0), self.image)

    def after_step(self):
        """React to a single step. Copy the current configuration into the
        :attr:`display_queue` and schedule a call to :meth:`paintEvent`."""
        conf = self.sim.get_config().copy()
        try:
            self.display_queue.put_nowait(conf)
        except Queue.Full:
            # the queue is initialised to hold as much lines as the
            # screen does. if we have more changes queued up than can
            # fit on the screen, we can just skip some of them.
            self.display_queue.get()
            self.display_queue.put(conf)
            # theoretically, in this case, the queued steps var would
            # have to be treated in a special way so that the update
            # line wanders around so that it still works, but
            # since the whole screen will get updated anyway, we
            # don't need to care at all.

        self.queued_steps += 1
        self.update(QRect(
            QPoint(0, ((self.last_step + self.queued_steps - 1) % self.img_height) * self.img_scale),
            QSize(self.img_width * self.img_scale, self.img_scale)))

    def conf_changed(self):
        """React to a change in the configuration that was not caused by a step
        of the cellular automaton - by a user interaction for instance."""
        self.after_step()
        self.update_no_step = True

class TwoDimDisplayWidget(BaseDisplayWidget):
    """A display widget for two-dimensional configurations."""
    def __init__(self, simulator, scale=1, **kwargs):
        super(TwoDimDisplayWidget, self).__init__(width=simulator.shape[0],
                    height=simulator.shape[1],
                    queue_size=1,
                    scale=scale,
                    **kwargs)

        self.sim = simulator
        self.conf_new = True
        self.queued_conf = simulator.get_config()

        self.drawing = False
        self.last_draw_pos = QPoint(0,0)

    def paintEvent(self, ev):
        """Get new configurations, update the internal pixmap, refresh the
        display.

        This is called from Qt whenever a repaint is in order. Do not call it
        yourself. :meth:`after_step` will call update, which will trigger a
        :meth:`paintEvent`.

        .. note::
            Only the very latest config will be displayed. All others will be
            dropped immediately."""
        if self.conf_new:
            conf = self.queued_conf
            self.conf_new = False
            w, h = conf.shape
            nconf = np.empty((w, h, 2), np.uint8, "C")
            if not self.invert_odd or self.odd:
                nconf[...,0] = conf * 255
            else:
                nconf[...,0] = 255 - conf * 255
            nconf[...,1] = nconf[...,0]
            self.image = QImage(nconf.data, w, h, QImage.Format_RGB444).scaled(
                    w * self.img_scale, h * self.img_scale)
            self.odd = not self.odd

        copier = QPainter(self)
        copier.drawImage(QPoint(0, 0), self.image)
        del copier

    def after_step(self):
        """React to a single step. Set the :attr:`queued_conf` to a copy of the
        current config and trigger a :meth:`paintEvent`."""
        conf = self.sim.get_config().copy()
        self.queued_conf = conf
        self.conf_new = True

        self.update()

    def conf_changed(self):
        self.after_step()

    def mousePressEvent(self, event):
        self.drawing = True
        self.last_draw_pos = (event.x() / self.img_scale, event.y() / self.img_scale)

    def mouseReleaseEvent(self, event):
        self.drawing = False

    def leaveEvent(self, event):
        self.drawing = False

    def mouseMoveEvent(self, event):
        new_draw_pos = (event.x() / self.img_scale, event.y() / self.img_scale)
        if self.last_draw_pos != new_draw_pos:
            self.sim.set_config_value(new_draw_pos)

