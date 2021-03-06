from ..external.qt import QWidget, QPixmap, QDockWidget, QScrollArea, QSize, QEvent, QPainter, Qt

class BaseExtraDisplay(QDockWidget):
    """The base class for a dockable/undockable/tabbable extra display widget
    for things such as histograms."""
    def __init__(self, title, sim, width, height, parent=None, **kwargs):
        super(BaseExtraDisplay, self).__init__(unicode(title))
        self.display_widget = QWidget(self)
        self.scroller = QScrollArea(self)
        self.scroller.setWidget(self.display_widget)
        self.display_widget.setFixedSize(QSize(width, height))
        self.scroller.setMinimumWidth(width + 5)
        self.scroller.setMinimumHeight(height + 5)
        self.setWidget(self.scroller)

        self.setAllowedAreas(Qt.RightDockWidgetArea)
        self.setFloating(False)

        self.display_widget.installEventFilter(self)

        self.display_widget.setAttribute(Qt.WA_OpaquePaintEvent)
        self.display_widget.setAttribute(Qt.WA_NoSystemBackground)

        self.sim = sim
        self.img_width, self.img_height = width, height

        self.create_image_surf()

    def eventFilter(self, widget, event):
        if widget == self.display_widget:
            if event.type() == QEvent.Type.Paint:
                self.child_paintEvent(event)
                return True
        return False

    def child_paintEvent(self, event):
        copier = QPainter(self.display_widget)
        copier.drawPixmap(event.rect(), self.display._image, event.rect())
        del copier

    def create_image_surf(self):
        """Create the image surface to use."""
        self.image = QPixmap(self.img_width, self.img_height)
        self.image.fill(0)

    def paint_display_widget(self, event):
        raise NotImplementedError("painting %s not implemented" % self)

    def after_step(self):
        pass

