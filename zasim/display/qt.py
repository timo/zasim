"""This module offers the `BaseQImageRenderer` base class and its two
subclasses `OneDimQImageRenderer` for rendering one-dimensional configs and
`TwoDimQImageRenderer` for rendering two-dimensional configs to QImages.

These classes also offer a _repr_png_ method, that is used by IPython to display
configurations in-line."""

from __future__ import absolute_import

from ..external.qt import (QObject, QPixmap, QImage, QPainter, QPoint, QSize, QRect,
                           QPen, QBrush, QLine, QColor, QBuffer, QIODevice, Signal, Qt)

import numpy as np
import time
import math
import Queue

from itertools import product

def generate_tile_atlas(filename_map, common_prefix=""):
    """From a mapping to state value to filename, create a texture atlas
    from the given filenames. Those should all be as big as the first one.

    :returns: The tile atlas as a QPixmap and a mapping from value to a
              QRect into the image.
    """
    # use the size of the first tile for every tile.
    size = QImage(filename_map.values()[0]).rect()
    one_w, one_h = size.width(), size.height()

    # try to make the image as near to a square image a spossible
    columns = int(math.ceil(math.sqrt(len(filename_map))))
    rows = len(filename_map) / columns + 1

    new_image = QPixmap(QSize(columns * one_w, rows * one_h))
    palette_rect = {}

    ptr = QPainter(new_image)
    ptr.fillRect(new_image.rect(), QBrush("pink"))
    for num, (value, name) in enumerate(filename_map.iteritems()):
        img = QImage(name)

        if img.isNull():
            print "warning:", name, "not found."

            # draw a bright error image with a bit of text
            img = QImage(one_w, one_h, QImage.Format_RGB32)
            img.fill(0xffff00ff)
            errptr = QPainter(img)
            errptr.setPen(QPen("white"))
            fnt = errptr.font()
            fnt.setPixelSize(30)
            errptr.setFont(fnt)
            name = name[len(common_prefix):] if name.startswith(common_prefix) else name
            errptr.drawText(QRect(0, 0, one_w, one_h), Qt.AlignCenter, u"ERROR\nnot found:\n%s\n:(" % (name))
            errptr.end()

        position_rect = QRect(one_w * (num / rows), one_h * (num % rows), one_w, one_h)
        ptr.drawImage(position_rect, img, img.rect())
        #palette_pf[nameStateDict[name]] = lambda x, y: QPainter.PixmapFragment.create(
                #QPointF(x, y),
                #position_rect)
        palette_rect[value] = position_rect

    ptr.end()

    return new_image, palette_rect

PALETTE_32 = dict(enumerate([0xff000000, 0xffffffff, 0xffff0000, 0xff0000ff, 0xff00ff00, 0xffffff00, 0xff00ffff, 0xffff00ff]))

def make_palette_qc(pal):
    """Turn a 32bit color palette into a QColor palette."""
    result = {}
    if isinstance(pal, list):
        pal = dict(enumerate(pal))
    for val, color in pal.iteritems():
        b = color & 0xff
        color = color >> 8
        g = color & 0xff
        color = color >> 8
        r = color & 0xff

        result[val] = QColor.fromRgb(r, g, b)

    return result

def make_palette_32(pal):
    """Turn a qcolor palette into a 32bit color palette."""
    result = {}
    if isinstance(pal, list):
        pal = dict(enumerate(pal))

    for val, color in pal.iteritems():
        # first 2 byte are ff
        res = 255
        res = res << 8
        res += color.red()
        res = res << 8
        res += color.green()
        res = res << 8
        res += color.blue()
        res = res << 8

        result[val] = res

    return result

def make_gray_palette(number_or_values):
    """Generates a grayscale with `number` entries.
    Alternatively, accept a list or dictionary with values.

    :returns: the RGB_32 palette and the QColor palette
    """
    if isinstance(number_or_values, int):
        keys = range(number_or_values)

    elif isinstance(number_or_values, list):
        keys = number_or_values

    elif isinstance(number_or_values, dict):
        keys = number_or_values.keys()

    number = len(keys)

    if number - 1 > 0xff:
        raise ValueError("cannot make 16bit grayscale with %d numbers" % number)

    pal_32 = {}
    pal_qc = {}
    for i, key in enumerate(keys):
        perc = 1.0 * i / (number - 1)
        of_32 = int(0xff * perc)
        pal_32[key] = of_32 + (of_32 << 8) + (of_32 << 16)
        pal_qc[key] = QColor.fromRgbF(perc, perc, perc)

    return pal_32, pal_qc



PALETTE_QC = make_palette_qc(PALETTE_32)

def qimage_to_pngstr(image):
    buf = QBuffer()
    buf.open(QIODevice.ReadWrite)
    image.save(buf, "PNG")
    buf.close()
    return str(buf.data())

_last_rendered_state_conf = None
def render_state_array(states, palette=PALETTE_32, region=None):
    global _last_rendered_state_conf
    if len(states.shape) == 1:
        states = states.reshape((states.shape[0], 1))
    if region:
        x, y, w, h = region
        conf = states[x:x+w, y:y+h]
    else:
        x, y = 0, 0
        w, h = states.shape
        conf = states
    nconf = np.empty((w, h), np.uint32, "F")

    for num, value in palette.iteritems():
        nconf[conf == num] = value

    image = QImage(nconf.data, w, h, QImage.Format_RGB32)

    # without this cheap trick, the data from the array is imemdiately freed and
    # subsequently re-used, leading to the first pixels in the top left corner
    # getting pretty colors and zasim eventually crashing.
    _last_rendered_state_conf = nconf
    return image

def render_state_array_tiled(states, palette, rects, region=None, painter=None):
    """Using a texture atlas and a dictionary of pixmap fragment "factories",
    draw a configuration using graphical tiles.

    :param states: The array of states to render.
    :param palette: The image to use.
    :param rects: A dictionary from state value to rect in the image.
    :param region: What part of the config to render (x, y, w, h).
    """

    if region:
        x, y, w, h = region
        try:
            conf = states[x:x+w, y:y+h]
        except IndexError:
            # this is 1d :(
            assert h == 1
            states = states.reshape((states.shape[0], h))
            conf = states[x:x+w, y:y+h]

        w, h = conf.shape
    else:
        x, y = 0, 0
        try:
            w, h = states.shape
        except ValueError:
            # the shape is 1d only
            w, = states.shape
            h = 1
            states = states.reshape((w,h))
        conf = states

    if not painter:
        tilesize = rects.values()[0].size()
        result = QPixmap(QSize(w * tilesize.width(), h * tilesize.height()))
        painter =  QPainter(result)
        painter.scale(tilesize.width(), tilesize.height())

    positions = product(xrange(w), xrange(h))

    values = [(pos, conf[pos]) for pos in positions]
    fragments = [(QPoint(pos[0], pos[1]), rects[value]) for pos, value in values]

    for dest, src in fragments:
        painter.drawPixmap(QRect(dest, QSize(1, 1)), palette, src)

    if not painter:
        return result

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

        if 'colors32' not in self._sim.palette_info:
            if len(self._sim.t.possible_values) > len(PALETTE_32):
                self.palette = make_gray_palette(self._sim.t.possible_values)
            else:
                self.palette = PALETTE_32
            self._sim.palette_info['colors32'] = self.palette
        else:
            self.palette = self._sim.palette_info['colors32']

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

    image_wrapped = Signal()
    """Emitted whenever the drawing position wraps around."""

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

                if whole_conf is None:
                    whole_conf = np.zeros((w, confs_to_render), dtype=conf.dtype)

                whole_conf[...,rendered] = conf

                rendered += 1

                if update_step:
                    self._last_step += 1

        except Queue.Empty:
            pass

        if not rendered:
            return

        self._queued_steps -= rendered
        _image = render_state_array(whole_conf, self.palette, (0, 0, w, rendered))
        _image = _image.scaled(w * self._scale, rendered * self._scale)

        painter = QPainter(self._image)
        painter.drawImage(QPoint(0, y * self._scale), _image)

        if self._last_step % self._height == 0 and rendered:
            self.image_wrapped.emit()

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

class TwoDimQImagePainterBase(BaseQImagePainter):
    """This class offers rendering a two-dimensional simulator config to
    a QImage"""

    _changed_rect = QRect()

    def after_step(self, update_step=True):
        if self._sim.changeinfo:
            self._changed_rect = self._changed_rect.united(QRect(*self._sim.changeinfo))

        if update_step and self.skip_frame():
            return
        conf = self._sim.get_config().copy()
        self._queue.put((update_step, conf, self._changed_rect))

        self.draw_conf()
        if self._changed_rect:
            coords = self._changed_rect.getRect()
            scaled_rect = QRect(*[coord * self._scale for coord in coords])
            self.update.emit(scaled_rect)
        else:
            self.update.emit(QRect(QPoint(0, 0), QSize(self._width, self._height)))

        self._changed_rect = QRect()

    def create_image_surf(self):
        pass

class TwoDimQImagePainter(TwoDimQImagePainterBase):
    def __init__(self, simulator, connect=True, **kwargs):
        """Initialise the TwoDimQImagePainter.

        :param simulator: The simulator to use.
        :param connect: Connect the painter to the simulators change signals?
        """
        self._sim = simulator
        w, h = simulator.shape

        super(TwoDimQImagePainter, self).__init__(w, h, queue_size=1, **kwargs)

    def draw_conf(self):
        try:
            update_step, conf, changeinfo = self._queue.get_nowait()
            if changeinfo:
                x, y, w, h = changeinfo.getRect()
                conf = conf[x:x+w, y:y+h]
            else:
                x, y = 0, 0
                w, h = self._width, self._height

            image = render_state_array(conf, self.palette, (0, 0, w, h))
            if changeinfo:
                painter = QPainter(self._image)
                if self._scale != 1:
                    painter.scale(self._scale, self._scale)
                painter.drawImage(QPoint(x, y), image)
                painter.end()
            else:
                pixmap = QPixmap.fromImage(image.copy())
                if self._scale != 1:
                    pixmap = pixmap.scaled(w * self._scale, h * self._scale)

                self._image = pixmap

        except Queue.Empty:
            pass

class TwoDimQImagePalettePainter(TwoDimQImagePainterBase):
    def __init__(self, simulator, scale=0.1, **kwargs):
        self._sim = simulator

        if 'tiles' in self._sim.palette_info:
            self.palette = self._sim.palette_info['tiles']['images']
            self.rects = self._sim.palette_info['tiles']['rects']
        else:
            raise NotImplementedError("There is no default image palette yet.")

        self.tile_size = self.rects.values()[0].height()
        assert self.rects.values()[0].width() == self.tile_size

        w, h = simulator.shape
        w = w * self.tile_size
        h = h * self.tile_size

        super(TwoDimQImagePalettePainter, self).__init__(w, h, **kwargs)

    def draw_conf(self):
        try:
            update_step, conf, changeinfo = self._queue.get_nowait()
            tilesize = self.tile_size * self._scale
            w, h = self._width / tilesize, self._height / tilesize

            print self._width, self._height, tilesize
            print w, h

            self._image = render_state_array_tiled(conf, self.palette, self.rects)
        except Queue.Empty:
            pass

# TODO make a painter that continuously moves up the old configurations for saner
#      display in ipython rich consoles and such.

class HistogramPainter(BaseQImagePainter):
    """The HistogramPainter draws an attribute from the simulator that's an array
    of constant length as stacked, colored bars, so that the horizontal axis is
    the time and the vertical axis is the amount."""

    image_wrapped = Signal()
    """Emitted whenever the drawing position wraps around."""

    def __init__(self, simulator, attribute, width, height, queue_size=1, connect=True, **kwargs):
        self._sim = simulator
        self._attribute = attribute
        self._linepos = 0
        if 'qcolors' not in self._sim.palette_info:
            if 'colors32' in self._sim.palette_info:
                self.colors = make_palette_qc(self._sim.palette_info['colors32'])
            else:
                raise ValueError("The simulator needs either qcolors or colors32 in its palette_info")
            self._sim.palette_info['qcolors'] = self.colors
        else:
            self.colors = self._sim.palette_info['qcolors']

        super(HistogramPainter, self).__init__(width, height, queue_size, connect=connect, **kwargs)

    def draw_conf(self):
        painter = QPainter(self._image)
        linepos = self._linepos
        try:
            while True:
                update_step, values = self._queue.get_nowait()
                maximum = sum(values)
                if not maximum:
                    values = [1] + (len(values) - 1) * [0]
                    maximum = 1
                scale = self._height * 1.0 / maximum
                absolute = 0.0
                for value, color in zip(values, self.colors.values()):
                    value = value * scale
                    painter.setPen(color)
                    painter.drawLine(QLine(linepos, absolute,
                                     linepos, absolute + value))
                    absolute += value

                if update_step:
                    linepos += 1
                    if linepos >= self._width:
                        linepos = 0
                        self.image_wrapped.emit()
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
