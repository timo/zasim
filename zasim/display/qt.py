from __future__ import absolute_import

from ..external.qt import (QObject, QImage, QPainter, QPoint, QSize, QRect,
                           QColor, QBuffer, QIODevice, Signal)

import numpy as np
import Queue

"""This module offers drawing capabilities for any image format that QImage
supports, such as png and jpg."""

PALETTE_444 = [0x0, 0xfff, 0xf00, 0x00f, 0x0f0, 0xff0, 0x0ff, 0xf0f]

def make_palette_qc():
    result = []
    for color in PALETTE_444:
        b = (color & 0xf) << 4 | (color & 0xf)
        color = color >> 4
        g = (color & 0xf) << 4 | (color & 0xf)
        color = color >> 4
        r = (color & 0xf) << 4 | (color & 0xf)

        result.append(QColor.fromRgb(r, g, b))

    return result

PALETTE_QC = make_palette_qc()

del make_palette_qc

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
        self._scale = scale

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
        if self._scale != scale:
            self._scale = scale
            self._image = self._image.scaled(self._width * scale, self._height * scale)

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

    def export(self, filename):
        if not self._image.save(filename):
            # TODO find out what caused the error
            raise Exception("Could not save image to file.")

    def _repr_png_(self):
        """For IPython, display the image as an embedded image."""
        buf = QBuffer()
        buf.open(QIODevice.ReadWrite)
        self._image.save(buf, "PNG")
        buf.close()
        return str(buf.data())

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
        self._last_step = 0

        self.palette = PALETTE_444[2:len(self._sim.t.possible_values)]

        super(LinearQImagePainter, self).__init__(
                simulator.shape[0], lines, lines,
                **kwargs)


    def draw_conf(self):
        rendered = 0
        y = self._last_step % self._height
        w = self._width
        scale = self._scale
        peek = None
        try:
            painter = QPainter(self._image)
            while rendered < min(100, self._height):
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

                nconf = np.empty((w, 1), np.uint16, "C")

                if not self._invert_odd or self._odd:
                    nconf[conf==0] = 0
                    nconf[conf==1] = 0xfff
                else:
                    nconf[conf==1] = 0
                    nconf[conf==0] = 0xfff

                for num, value in enumerate(self.palette):
                    nconf[conf == num+2] = value

                _image = QImage(nconf.data, w, 1, QImage.Format_RGB444).scaled(w * scale, scale)
                painter.drawImage(QPoint(0, y * scale), _image)

                self._queued_steps -= 1
                rendered += 1
                if update_step:
                    self._last_step += 1
                    y = self._last_step % self._height
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
            QPoint(0, ((self._last_step + self._queued_steps - 1) % self._height) * self._scale),
            QSize(self._width * self._scale, self._scale)))

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

        self.palette = PALETTE_444[2:len(self._sim.t.possible_values)]

        if connect:
            self.connect_simulator()

    def draw_conf(self):
        try:
            update_step, conf = self._queue.get_nowait()
            self.conf_new = False
            w, h = self._width, self._height
            nconf = np.empty((w, h), np.uint16, "C")

            if not self._invert_odd or self._odd:
                nconf[conf==0] = 0
                nconf[conf==1] = 0xfff
            else:
                nconf[conf==1] = 0
                nconf[conf==0] = 0xfff

            for num, value in enumerate(self.palette):
                nconf[conf == num+2] = value

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
