from ..external.qt import QGLWidget, QImage, QDockWidget, QScrollArea, QSize, QEvent, Qt
import Queue

class BaseDisplayWidget(QGLWidget):
    """A base class for different types of displays.

    Manages the config display queue, scrolling, ..."""
    def __init__(self, width, height, queue_size=1, scale=1, **kwargs):
        """Initialize the BaseDisplayWidget.

        :param width: The width of the image to build.
        :param height: The height of the image to build.
        :param queue_size: The amount of histories that may pile up before
                           forcing a redraw.
        """
        super(BaseDisplayWidget, self).__init__(**kwargs)
        self.img_width, self.img_height = width, height
        self.set_scale(scale)

        self.create_image_surf()
        self.display_queue = Queue.Queue(queue_size)

        self.last_step = 0
        self.queued_steps = 0

        self.invert_odd = False
        self.odd = False

    def start_inverting_frames(self): self.invert_odd = True
    def stop_inverting_frames(self): self.invert_odd = False

    def create_image_surf(self):
        """Create the image surface when the display is created."""
        self.image = QImage(self.img_width * self.img_scale,
                            self.img_height * self.img_scale,
                            QImage.Format_RGB444)
        self.image.fill(0)

    def set_scale(self, scale):
        """Change the scale of the display."""
        self.img_scale = scale
        self.resize(self.img_width * self.img_scale,
                    self.img_height * self.img_scale)
        self.create_image_surf()

class BaseExtraDisplay(QDockWidget):
    """The base class for a dockable/undockable/tabbable extra display widget
    for things such as histograms."""
    def __init__(self, title, sim, width, height, parent=None, **kwargs):
        super(BaseExtraDisplay, self).__init__(unicode(title))
        self.display_widget = QGLWidget(self)
        self.scroller = QScrollArea(self)
        self.scroller.setWidget(self.display_widget)
        self.display_widget.setFixedSize(QSize(width, height))
        self.scroller.setMinimumWidth(width + 5)
        self.scroller.setMinimumHeight(height + 5)
        self.setWidget(self.scroller)

        self.setAllowedAreas(Qt.RightDockWidgetArea)
        self.setFloating(False)

        self.display_widget.installEventFilter(self)

        self.sim = sim
        self.img_width, self.img_height = width, height

        self.create_image_surf()

    def eventFilter(self, widget, event):
        if widget == self.display_widget:
            if event.type() == QEvent.Type.Paint:
                self.paint_display_widget(event)
                return True
        return False

    def create_image_surf(self):
        """Create the image surface to use."""
        self.image = QImage(self.img_width, self.img_height,
                            QImage.Format_RGB444)
        self.image.fill(0)

    def paint_display_widget(self, event):
        raise NotImplementedError("painting %s not implemented" % self)

    def after_step(self):
        pass

