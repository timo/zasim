from __future__ import absolute_import

from ..external.qt import QObject, QImage, QPainter, QPoint, QSize, QRect, Signal

import numpy as np
import Queue

"""This module offers drawing capabilities for different formats."""

class BaseQImagePainter(QObject):

    update = Signal(["QRect"])

    def __init__(self, width, height, queue_size=1, scale=1, **kwargs):
        """Initialize the BaseDisplayWidget.

        :param width: The width of the image to build.
        :param height: The height of the image to build.
        :param queue_size: The amount of histories that may pile up before
                           forcing a redraw.
        """
        super(BaseQImagePainter, self).__init__(**kwargs)
        self._width, self._height = width, height
        self.set_scale(scale)

        self.create_image_surf()
        self._queue = Queue.Queue(queue_size)

        self._last_step = 0
        self._queued_steps = 0

        self._invert_odd = False
        self._odd = False

    def create_image_surf(self):
        """Create the image surface when the display is created."""
        self._image = QImage(self._width * self._scale,
                             self._height * self._scale,
                             QImage.Format_RGB444)
        self._image.fill(0)

    def set_scale(self, scale):
        """Change the scale of the display."""
        self._scale = scale
        self.create_image_surf()

    def start_inverting_frames(self): self._invert_odd = True
    def stop_inverting_frames(self): self._invert_odd = False

class LinearQImagePainter(BaseQImagePainter):
    """This class offers drawing for one-dimensional cellular automata, which
    will fill up the display with a line that moves downwards and wraps at the
    bottom."""

    def __init__(self, simulator, lines=None, connect=True, **kwargs):
        self._sim = simulator
        if lines is None:
            lines = simulator.shape[0]

        super(LinearQImagePainter, self).__init__(
                simulator.shape[0], lines, lines,
                **kwargs)

        if connect:
            self.connect_simulator()

    def connect_simulator(self):
        self._sim.changed.connect(self.conf_changed)
        self._sim.updated.connect(self.after_step)

    def draw_conf(self):
        rendered = 0
        y = self.last_step % self._height
        w = self._width
        scale = self._scale
        peek = None
        try:
            painter = QPainter(self._image)
            while rendered < min(100, self.img_height):
                update_step, conf = peek or self._queue.get_nowait()

                if not update_step:
                    # try skipping configurations that don't need updating.
                    try:
                        while True:
                            update_next_step, next_conf = self._queue.get_nowait()
                            if update_next_step:
                                peek = (update_next_step, next_conf)
                                break
                    except Queue.Empty:
                        pass

                nconf = np.empty((w, 1, 2), np.uint8, "C")
                if not self._invert_odd or self._odd:
                    nconf[...,0,0] = conf * 255
                else:
                    nconf[...,0,0] = (1 - conf) * 255
                nconf[...,1] = nconf[...,0]

                _image = QImage(nconf.data, w, 1, QImage.Format_RGB444).scaled(w * scale, scale)
                painter.drawImage(QPoint(0, y * scale), _image)

                self.queued_steps -= 1
                rendered += 1
                if update_step:
                    self.last_step += 1
                    y = self.last_step % self.img_height
                    self._odd = not self._odd
        except Queue.Empty:
            pass

    def after_step(self, update_step=True):
        conf = self._sim.get_config().copy()
        try:
            self._queue.put_nowait(conf)
        except Queue.Full:
            # the queue is initialised to hold as much lines as the
            # screen does. if we have more changes queued up than can
            # fit on the screen, we can just skip some of them.
            self._queue.get()
            self._queue.put((update_step, conf))
            # theoretically, in this case, the queued steps var would
            # have to be treated in a special way so that the update
            # line wanders around so that it still works, but
            # since the whole screen will get updated anyway, we
            # don't need to care at all.

        self._queued_steps += 1
        self.update.emit(QRect(
            QPoint(0, ((self.last_step + self.queued_steps - 1) % self.img_height) * self.img_scale),
            QSize(self.img_width * self.img_scale, self.img_scale)))

    def conf_changed(self):
        """React to a change in the configuration that was not caused by a step
        of the cellular automaton - by a user interaction for instance."""
        self.after_step(False)

class TwoDimQImagePainter(BaseQImagePainter):
    def __init__(self, simulator, connect=True, **kwargs):
        self._sim = simulator
        w, h = simulator.shape
        super(TwoDimQImagePainter, self).__init__(w, h, queue_size=1, **kwargs)

        if connect:
            self.connect_simulator()

    def draw_conf(self):
        try:
            conf = self._queue.get_nowait()
            self.conf_new = False
            w, h = self._width, self._height
            nconf = np.empty((w, h, 2), np.uint8, "C")
            if not self._invert_odd or self._odd:
                nconf[...,0] = conf * 255
            else:
                nconf[...,0] = 255 - conf * 255
            nconf[...,1] = nconf[...,0]
            self._image = QImage(nconf.data, w, h, QImage.Format_RGB444).scaled(
                    w * self._scale, h * self._scale)
            self._odd = not self._odd
        except Queue.Empty:
            pass

    def connect_simulator(self):
        self._sim.updated.connect(self.after_step)
        self._sim.changed.connect(self.after_step)

    def after_step(self):
        conf = self._sim.get_config().copy()
        try:
            self._queue.put_nowait(conf)
        except Queue.Full:
            self._queue.get()
            self._queue.put(conf)

        self.update.emit(QRect(QPoint(0, 0), QSize(self._width, self._height)))
