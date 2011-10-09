from ..external.qt import QWidget, QPainter, Qt
from ..display.qt import OneDimQImagePainter, TwoDimQImagePainter

class DisplayWidget(QWidget):
    """A Display widget for one- and twodimensional configs.

    Based on `zasim.display.qt`"""

    def __init__(self, simulator, width=None, height=None, **kwargs):
        """Initialize the DisplayWidget.

        :param width: The width of the image to build.
        :param height: The height of the image to build.
        :param queue_size: The amount of histories that may pile up before
                           forcing a redraw.
        """
        super(DisplayWidget, self).__init__(**kwargs)

        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WA_NoSystemBackground)

        self._sim = simulator

        scale = 1

        shape = simulator.shape
        if len(shape) == 1:
            if width is None:
                width = shape[0]
            else:
                scale = width / shape[0]
                assert shape[0] * scale == width, "Width not a whole multiple of config width"
            if height is None:
                height = width

            self.display = OneDimQImagePainter(simulator, height, scale=scale)

        elif len(shape) == 2:
            if width is None:
                width = shape[0]
            else:
                scale = width / shape[0]
                assert shape[0] * scale == width, "Width not a whole multiple of config width"
            if height is None:
                height = shape[1]
            else:
                if scale != 1:
                    assert shape[1] * scale == height, "Height does not match config height times scale value"
                else:
                    scale = height / shape[1]
                    assert shape[1] * scale == height, "Height not a whole multiple of config height"

            self.display = TwoDimQImagePainter(simulator, scale=scale)

        else:
            raise ValueError("Simulators with %d dimensions are not supported for display" % len(shape))

        self._scale = scale
        self._width = width
        self._height = height

        self._scale_scroll = 0

        self.display.setObjectName("display")
        self.display.update.connect(self.update)

    def start_inverting_frames(self): self.display.start_inverting_frames()
    def stop_inverting_frames(self): self.display.stop_inverting_frames()

    def set_scale(self, scale):
        self._scale = scale
        self.display.set_scale(scale)
        self.setFixedSize(self._width * scale, self._height * scale)

    def paintEvent(self, event):
        copier = QPainter(self)
        copier.drawPixmap(event.rect(), self.display._image, event.rect())
        del copier

    def mousePressEvent(self, event):
        self.drawing = True
        self.last_draw_pos = (event.x() / self._scale, event.y() / self._scale)

    def mouseReleaseEvent(self, event):
        self.drawing = False

    def leaveEvent(self, event):
        self.drawing = False

    def mouseMoveEvent(self, event):
        new_draw_pos = (event.x() / self._scale, event.y() / self._scale)
        if len(self._sim.shape) == 1:
            if self.last_draw_pos[0] != new_draw_pos[0]:
                self._sim.set_config_value(new_draw_pos[0])
        else:
            if self.last_draw_pos != new_draw_pos:
                self._sim.set_config_value(new_draw_pos[::-1])

    def wheelEvent(self, event):
        num_degrees = event.delta() / 8.
        num_steps = num_degrees / 15

        if event.orientation() == Qt.Horizontal:
            event.ignore()
        else:
            self._scale_scroll += num_steps

        if self._scale_scroll > 1:
            self._scale += 1
            self._scale_scroll = 0
        elif self._scale_scroll < 1:
            self._scale -= 1
            self._scale_scroll = 0

        if self._scale < 1:
            self._scale = 1
        elif self._scale > 50:
            self._scale = 50

        self.set_scale(self._scale)

    def export(self, filename):
        return self.display.export(filename)
