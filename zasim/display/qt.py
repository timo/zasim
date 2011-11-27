"""This module offers the `BaseQImageRenderer` base class and its two
subclasses `OneDimQImageRenderer` for rendering one-dimensional configs and
`TwoDimQImageRenderer` for rendering two-dimensional configs to QImages.

These classes also offer a _repr_png_ method, that is used by IPython to display
configurations in-line."""

from __future__ import absolute_import

from ..external.qt import (QObject, QPixmap, QImage, QPainter, QPoint, QSize, QRect,
                           QLine, QColor, QBuffer, QIODevice, Signal, Qt)

import numpy as np
import time
import Queue


PALETTE_32 = [0xff000000, 0xffffffff, 0xffff0000, 0xff0000ff, 0xff00ff00, 0xffffff00, 0xff00ffff, 0xffff00ff]

def make_palette_qc(pal):
    result = []
    for color in pal:
        b = color & 0xff
        color = color >> 8
        g = color & 0xff
        color = color >> 8
        r = color & 0xff

        result.append(QColor.fromRgb(r, g, b))

    return result

def make_gray_palette(number):
    """Generates a grayscale with `number` entries.

    :returns: the RGB_32 palette and the QColor palette
    """
    if number - 1 > 0xff:
        raise ValueError("cannot make 16bit grayscale with %d numbers" % number)

    pal_32 = []
    pal_qc = []
    for i in range(number):
        perc = 1.0 * i / (number - 1)
        of_32 = int(0xff * perc)
        pal_32.append(of_32 + (of_32 << 8) + (of_32 << 16))
        pal_qc.append(QColor.fromRgbF(perc, perc, perc))

    return pal_32, pal_qc

PALETTE_QC = make_palette_qc(PALETTE_32)

def qimage_to_pngstr(image):
    buf = QBuffer()
    buf.open(QIODevice.ReadWrite)
    image.save(buf, "PNG")
    buf.close()
    return str(buf.data())

def render_state_array(states, palette=PALETTE_QC, invert=False, region=None):
    if region:
        x, y, w, h = region
        conf = states[x:x+w, y:y+h]
    else:
        x, y = 0
        w, h = states.shape
        conf = states
    nconf = np.empty((w - x, h - y), np.uint32, "F")

    if not invert:
        nconf[conf==0] = palette[0]
        nconf[conf==1] = palette[1]
    else:
        nconf[conf==1] = palette[0]
        nconf[conf==0] = palette[1]

    for num, value in enumerate(palette[2:]):
        nconf[conf == num+2] = value

    image = QImage(nconf.data, w - x, h - y, QImage.Format_RGB32)
    return image

class BaseQImagePainter(QObject):
    """This is a base class for implementing renderers for configs based on
    QImage."""

    update = Signal(["QRect"])
    """This signal will be emitted when the configuration has changed.

    Its first argument is the area of change as a QRect."""

    def __init__(self, width, height, queue_size=1, scale=1,
                 connect=True, frame_duration=1.0/50, **kwargs):
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

        self.desired_frame_duration = frame_duration
        self.next_frame = 0

        if connect:
            self.connect_simulator()

    def create_image_surf(self):
        """Create the image surface when the display is created."""
        self._image = QPixmap(self._width * self._scale,
                             self._height * self._scale)
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
        self._sim.snapshot_restored.connect(self.conf_replaced)
        self._sim.updated.connect(self.after_step)
        self.conf_changed()

    def conf_changed(self):
        """React to a change in the configuration that was not caused by a step
        of the cellular automaton - by a user interaction for instance."""
        self.after_step(False)

    def conf_replaced(self):
        """React to snapshot_restored.

        This implementation just calls conf_changed."""
        self.conf_changed()

    def export(self, filename):
        if not self._image.save(filename):
            # TODO find out what caused the error
            raise Exception("Could not save image to file.")

    def _repr_png_(self):
        """For IPython, display the image as an embedded image."""
        return qimage_to_pngstr(self._image)

    def skip_frame(self):
        """Returns True, if the frame is supposed to be skipped to reach the
        desired framerate."""
        now = time.time()
        if now > self.next_frame:
            self.next_frame = now + self.desired_frame_duration
            return False
        return True

class OneDimQImagePainter(BaseQImagePainter):
    """This class offers drawing for one-dimensional cellular automata, which
    will fill up the display with a line that moves downwards and wraps at the
    bottom."""

    def __init__(self, simulator, lines=None, connect=True, **kwargs):
        """Initialise the OneDimQImagePainter.

        :param simulator: The simulator to use.
        :param lines: The number of lines to display at once.
        :param connect: Should the painter be connected to the simulators
                        change signals?
        """
        self._sim = simulator
        if lines is None:
            lines = simulator.shape[0]
        self._last_step = 0

        self.palette = PALETTE_32[:len(self._sim.t.possible_values)]

        super(OneDimQImagePainter, self).__init__(
                simulator.shape[0], lines, lines,
                **kwargs)


    def draw_conf(self):
        rendered = 0
        y = self._last_step % self._height
        w = self._width
        peek = None

        confs_to_render = min(self._height - y, self._queued_steps)

        # create whole_conf lazily, so that we can derive the dtype from the confs
        whole_conf = None

        try:
            while rendered < confs_to_render:
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
                        if peek is None:
                            raise

                if not whole_conf:
                    whole_conf = np.zeros((w, confs_to_render), dtype=conf.dtype)

                if (self._invert_odd and self._odd):
                    new_zeros = conf == 1
                    new_ones = conf == 0
                    conf[new_zeros] = 0
                    conf[new_ones] = 1

                whole_conf[rendered,...] = conf

                rendered += 1

                if update_step:
                    self._last_step += 1
                    self._odd = not self._odd

        except Queue.Empty:
            pass

        self._queued_steps -= rendered
        _image = render_state_array(whole_conf, self.palette, False, (0, 0, w, rendered))
        _image = _image.scaled(w * self._scale, rendered * self._scale)

        painter = QPainter(self._image)
        painter.drawImage(QPoint(0, y * self._scale), _image)


    def after_step(self, update_step=True):
        conf = self._sim.get_config().copy()
        try:
            self._queue.put_nowait((update_step, conf))
            self._queued_steps += 1
            conf = None
        except Queue.Full:
            pass

        if not self.skip_frame() or conf is not None or not update_step:

            self.draw_conf()
            self.update.emit(QRect(
                QPoint(0, ((self._last_step + self._queued_steps - 1) % self._height) * self._scale),
                QSize(self._width * self._scale, self._scale)))

        if conf is not None:
            self._queue.put((update_step, conf))
            self._queued_steps += 1
            conf = None

    def conf_replaced(self):
        # empty the queue
        while not self._queue.empty():
            self._queue.get()

        self._queued_steps = 0

        # set the position back to 0
        self._last_step = 0

        self.after_step(False)

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

        self.palette = PALETTE_32[:len(self._sim.t.possible_values)]
        super(TwoDimQImagePainter, self).__init__(w, h, queue_size=1, **kwargs)

    def draw_conf(self):
        try:
            update_step, conf = self._queue.get_nowait()
            w, h = self._width, self._height

            image = render_state_array(conf, self.palette, self._invert_odd and self._odd, (0, 0, w, h))
            image = QPixmap.fromImage(image)
            if self._scale != 1:
                image = image.scaled(w * self._scale, h * self._scale)
            self._image = image
            if update_step:
                self._odd = not self._odd
        except Queue.Empty:
            pass

    def after_step(self, update_step=True):
        if update_step and self.skip_frame():
            return
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
        self.palette = PALETTE_32[:len(self._sim.t.possible_values)]
        self.colors = make_palette_qc(self.palette)

        super(HistogramPainter, self).__init__(width, height, queue_size, connect=connect, **kwargs)

    def draw_conf(self):
        painter = QPainter(self._image)
        linepos = self._linepos
        try:
            while True:
                update_step, values = self._queue.get_nowait()
                if self._invert_odd and self._odd:
                    values = (values[1], values[0]) + tuple(values[1:])
                maximum = sum(values)
                if not maximum:
                    values = [1] + (len(values) - 1) * [0]
                    maximum = 1
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

        self._linepos = linepos

    def after_step(self, update_step=True):
        values = getattr(self._sim.t, self._attribute).copy()
        self._queue.put((update_step, values))

        self.draw_conf()
        urect = QRect(QPoint((self._linepos - 1) % self._width, 0),
                               QSize(1, self._height))
        self.update.emit(urect)

    def conf_replaced(self):
        while not self._queue.empty():
            self._queue.get()
        self._linepos = 0

        self.after_step(False)

def display_table(images, columns=1, captions=None, transparent=True):
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
                   QImage.Format_RGB32 if not transparent
                   else QImage.Format_ARGB32)
    if transparent:
        image.fill(0x00ffffff)
    else:
        image.fill(0xff000000)

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

            painter.drawPixmap(QPoint(x, y), img)
            rect = QRect(QPoint(x, y + row_heights[row]),
                         QSize(col_widths[col], 50))
            painter.drawText(rect, Qt.AlignCenter, unicode(captions[num]))

            x += col_widths[col] + 20
            if col == columns - 1:
                y += row_heights[row] + 60
    finally:
        painter.end()

    return image
