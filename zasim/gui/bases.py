from ..external.qt import QGLWidget, QImage, QDockWidget, QScrollArea, QSize, QEvent, Qt
import Queue

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

