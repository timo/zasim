from ..external.qt import QWidget, QPainter, Qt
from ..display.qt import OneDimQImagePainter, TwoDimQImagePainter, TwoDimQImagePalettePainter

from zasim.cagen.jvn import PALETTE_JVN_IMAGE, PALETTE_JVN_RECT

class DisplayWidget(QWidget):
    """A Display widget for one- and twodimensional configs.

    Based on `zasim.display.qt`"""

    def __init__(self, simulator, width=None, height=None, **kwargs):
        """Initialize the DisplayWidget.

        :param width: The width of the image to build.
        :param height: The height of the image to build.
        """
        super(DisplayWidget, self).__init__(**kwargs)

        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WA_NoSystemBackground)

        self._sim = simulator

        self._scale = 1
        self._width = width
        self._height = height

        self._create_painter()

        self._scale_scroll = 0

        self.display.setObjectName("display")
        self.display.update.connect(self.update)

    def _create_painter(self):
        shape = self._sim.shape

        if self._width is None:
            self._width = shape[0]
        else:
            self._scale = self._width / shape[0]
            assert shape[0] * self._scale == self._width, "Width not a whole multiple of config width"

        if len(shape) == 1:
            if self._height is None:
                self._height = self._width

            self.display = OneDimQImagePainter(self._sim, self._height, scale=self._scale)

        elif len(shape) == 2:
            if self._height is None:
                self._height = shape[1]
            else:
                if self._scale != 1:
                    assert shape[1] * self._scale == self._height, "Height does not match config height times scale value"
                else:
                    self._scale = self._height / shape[1]
                    assert shape[1] * self._scale == self._height, "Height not a whole multiple of config height"

            self.display = TwoDimQImagePainter(self._sim, scale=self._scale)

        else:
            raise ValueError("Simulators with %d dimensions are not supported for display" % len(shape))


    def switch_simulator(self, simulator):
        """This method replaces the previous simulator with `simulator`."""
        self._sim = simulator
        self._create_painter()
        self.set_scale(self._scale)
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
                self._sim.set_config_value(new_draw_pos)

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
