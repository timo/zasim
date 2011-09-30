"""This module offers the `BaseQImageRenderer` base class and its two
subclasses `LinearQImageRenderer` for rendering one-dimensional configs and
`TwoDimQImageRenderer` for rendering two-dimensional configs to QImages.

These classes also offer a _repr_png_ method, that is used by IPython to display
configurations in-line."""

from __future__ import absolute_import

from ..external.qt import (QObject, QImage, QPainter, QPoint, QSize, QRect,
                           QLine, QColor, QBuffer, QIODevice, Signal, Qt)

import numpy as np
import Queue


PALETTE_444 = [0x0, 0xfff, 0xf00, 0x00f, 0x0f0, 0xff0, 0x0ff, 0xf0f]

def make_palette_qc(pal):
    result = []
    for color in pal:
        b = (color & 0xf) << 4 | (color & 0xf)
        color = color >> 4
        g = (color & 0xf) << 4 | (color & 0xf)
        color = color >> 4
        r = (color & 0xf) << 4 | (color & 0xf)

        result.append(QColor.fromRgb(r, g, b))

    return result

def make_gray_palette(number):
    """Generates a grayscale with `number` entries.

    :returns: the RGB_444 palette and the QColor palette
    """
    if number - 1 > 0xf:
        raise ValueError("cannot make 4bit grayscale with %d numbers" % number)

    pal_444 = []
    pal_qc = []
    for i in range(number):
        perc = 1.0 * i / (number - 1)
        of_444 = int(0xf * perc)
        pal_444.append(of_444 + (of_444 << 4) + (of_444 << 8))
        pal_qc.append(QColor.fromRgbF(perc, perc, perc))

    return pal_444, pal_qc

PALETTE_QC = make_palette_qc(PALETTE_444)

def qimage_to_pngstr(image):
    buf = QBuffer()
    buf.open(QIODevice.ReadWrite)
    image.save(buf, "PNG")
    buf.close()
    return str(buf.data())


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
        self.conf_changed()

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
        return qimage_to_pngstr(self._image)

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

        self.draw_conf()
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

        self.palette = PALETTE_444[2:len(self._sim.t.possible_values)]
        super(TwoDimQImagePainter, self).__init__(w, h, queue_size=1, **kwargs)

    def draw_conf(self):
        try:
            update_step, conf = self._queue.get_nowait()
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

            image = QImage(nconf.data, w, h, QImage.Format_RGB444)
            if self._scale != 1:
                image = image.scaled(w * self._scale, h * self._scale)
            else:
                # XXX why does pyside want me to do this?
                image = image.copy()
            self._image = image
            if update_step:
                self._odd = not self._odd
        except Queue.Empty:
            pass

    def after_step(self, update_step=True):
        conf = self._sim.get_config().copy()
        self._queue.put((update_step, conf))

        self.draw_conf()
        self.update.emit(QRect(QPoint(0, 0), QSize(self._width, self._height)))

# TODO make a painter that continuously moves up the old configurations for saner
#      display in ipython rich consoles and such.

class HistogramPainter(BaseQImagePainter):
    def __init__(self, simulator, attribute, width, height, queue_size=1, connect=True, **kwargs):
        self._sim = simulator
        self._attribute = attribute
        self._linepos = 0
        self.palette = PALETTE_444[:len(self._sim.t.possible_values)]
        self.colors = make_palette_qc(self.palette)

        super(HistogramPainter, self).__init__(width, height, queue_size, connect=connect, **kwargs)

    def draw_conf(self):
        painter = QPainter(self._image)
        linepos = self._linepos
        try:
            while True:
                update_step, values = self._queue.get_nowait()
                if not self._invert_odd or self._odd:
                    values = (values[1], values[0]) + values[1:]
                maximum = sum(values)
                scale = self._height * 1.0 / maximum
                absolute = 0.0
                for value, color in zip(values, self.colors):
                    value = value * scale
                    painter.setPen(color)
                    painter.drawLine(QLine(linepos, absolute,
                                     linepos, absolute + value))
                    absolute += value

                if update_step:
                    linepos += 1
                    if linepos >= self._width:
                        linepos = 0
                        # don't jump across the border, just draw
                        # two lines the next time.
                        break

        except Queue.Empty:
            pass

        print linepos
        self._linepos = linepos

    def after_step(self, update_step=True):
        values = getattr(self._sim.t, self._attribute).copy()
        self._queue.put((update_step, values))

        self.draw_conf()
        urect = QRect(QPoint((self._linepos - 1) % self._width, 0),
                               QSize(1, self._height))
        print urect
        self.update.emit(urect)

def display_table(images, columns=1, captions=None):
    col_widths = [0 for col in range(columns)]
    row_heights = [0 for row in range(len(images) / columns + 1)]

    for num, img in enumerate(images):
        row = num / columns
        col = num % columns

        w, h = img.width(), img.height()

        col_widths[col] = max(col_widths[col], w)
        row_heights[row] = max(row_heights[row], h)

    image = QImage(sum(col_widths) + 20 * (columns - 1),
                   sum(row_heights) + 60 * (len(images) / columns),
                   QImage.Format_RGB444)
    image.fill(0xfff)

    if captions is None:
        captions = map(str, range(1, len(images) + 1))

    try:
        painter = QPainter(image)
        x, y = 0, 0
        for num, img in enumerate(images):
            row = num / columns
            col = num % columns
            if col == 0:
                x = 0

            painter.drawImage(QPoint(x, y), img)
            rect = QRect(QPoint(x, y + row_heights[row]),
                         QSize(col_widths[col], 50))
            painter.drawText(rect, Qt.AlignCenter, unicode(captions[num]))

            x += col_widths[col] + 20
            if col == columns - 1:
                y += row_heights[row] + 60
    finally:
        painter.end()

    return image
