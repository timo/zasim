from __future__ import absolute_import

from ..external.qt import QObject, QImage, QPainter, QPoint, QSize, QRect, Signal

import numpy as np
import Queue

"""This module offers drawing capabilities for different formats."""

class BaseQImagePainter(QObject):
    """This is a base class for implementing renderers for configs based on
    QImage."""

    update = Signal(["QRect"])
    """This signal will be emitted when the configuration has changed.

    Its first argument is the area of change as a QRect."""

    def __init__(self, width, height, queue_size=1, scale=1, connect=True, **kwargs):
        """Initialize the BaseQImagePainter.

        :param width: The width of the image to build.
        :param height: The height of the image to build.
        :param queue_size: The amount of histories that may pile up before
                           forcing a redraw.
        :param scale: The scale for the image.
        :param connect: Connect the update signals from the simulator?
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

        if connect:
            self.connect_simulator()

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

    def after_step(self, update_step=True):
        """Implement this in a subclass to fetch the config from the simulator.

        :param update_step: Was this update caused by a step or just a change?
        """

    def draw_conf(self):
        """Get the conf/confs enqueued/set by `after_step` and draw them to
        `_image`."""

    def start_inverting_frames(self): self._invert_odd = True
    def stop_inverting_frames(self): self._invert_odd = False

    def connect_simulator(self):
        self._sim.changed.connect(self.conf_changed)
        self._sim.updated.connect(self.after_step)

    def conf_changed(self):
        """React to a change in the configuration that was not caused by a step
        of the cellular automaton - by a user interaction for instance."""
        self.after_step(False)

class LinearQImagePainter(BaseQImagePainter):
    """This class offers drawing for one-dimensional cellular automata, which
    will fill up the display with a line that moves downwards and wraps at the
    bottom."""

    def __init__(self, simulator, lines=None, connect=True, **kwargs):
        """Initialise the LinearQImagePainter.

        :param simulator: The simulator to use.
        :param lines: The number of lines to display at once.
        :param connect: Should the painter be connected to the simulators
                        change signals?
        """
        self._sim = simulator
        if lines is None:
            lines = simulator.shape[0]

        super(LinearQImagePainter, self).__init__(
                simulator.shape[0], lines, lines,
                **kwargs)


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
        if self._queue.full():
            self._queue.get()
        self._queue.put((update_step, conf))

        self._queued_steps += 1
        self.update.emit(QRect(
            QPoint(0, ((self.last_step + self.queued_steps - 1) % self.img_height) * self.img_scale),
            QSize(self.img_width * self.img_scale, self.img_scale)))

class TwoDimQImagePainter(BaseQImagePainter):
    """This class offers rendering a two-dimensional simulator config to
    a QImage"""
    def __init__(self, simulator, connect=True, **kwargs):
        """Initialise the TwoDimQImagePainter.

        :param simulator: The simulator to use.
        :param connect: Connect the painter to the simulators change signals?
        """
        self._sim = simulator
        w, h = simulator.shape
        super(TwoDimQImagePainter, self).__init__(w, h, queue_size=1, **kwargs)

        if connect:
            self.connect_simulator()

    def draw_conf(self):
        try:
            update_step, conf = self._queue.get_nowait()
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
            if update_step:
                self._odd = not self._odd
        except Queue.Empty:
            pass

    def after_step(self, update_step=True):
        conf = self._sim.get_config().copy()
        if not self._queue.empty():
            self._queue.get()
        self._queue.put((update_step, conf))

        self.update.emit(QRect(QPoint(0, 0), QSize(self._width, self._height)))
