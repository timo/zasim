from __future__ import absolute_import

"""This module offers a display and interaction frontend with Qt.

It will try importing PySide first, and if that fails PyQt. The code will
constantly be tested with both bindings."""

from .ca import binRule

try:
    from PySide.QtCore import *
    from PySide.QtGui import *
    print "using pyside"
except ImportError:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    print "using pyqt4"
import Queue
import sys
import random
import time

class Control(QWidget):
    """Control a simulator with buttons or from the interactive console."""
    def __init__(self, simulator, parent=None):
        """:param simulator: The simulator object to control.
        :param parent: the QWidget to set as parent."""
        super(Control, self).__init__(parent)

        self.sim = simulator
        self.timer_delay = 10
        self.attached_displays = []

        self._setup_ui()

    def _setup_ui(self):
        """Setup the widgets, connect the signals&slots."""
        l = QHBoxLayout(self)
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setDisabled(True)
        delay = QSpinBox()
        delay.setValue(self.timer_delay)

        l.addWidget(self.start_button)
        l.addWidget(self.stop_button)
        l.addWidget(delay)
        self.setLayout(l)

        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        delay.valueChanged.connect(self.change_delay)

    def start(self):
        """Start running the simulator."""
        self.timer_id = self.startTimer(self.timer_delay)
        self.start_button.setDisabled(True)
        self.stop_button.setEnabled(True)

    def stop(self):
        """Stop the simulator."""
        self.killTimer(self.timer_id)
        self.stop_button.setDisabled(True)
        self.start_button.setEnabled(True)

    def change_delay(self, delay):
        """Change the timer delay of the simulator steps."""
        self.timer_delay = int(delay)

    def timerEvent(self, event):
        """Step the simulator from the timer.

        .. note::
            This is called by the timer that is controlled by :meth:`start` and
            :meth:`stop`. You should not call it yourself."""
        self.killTimer(self.timer_id)
        self.step()
        self.timer_id = self.startTimer(self.timer_delay)

    def step(self):
        """Step the simulator, update all displays."""
        self.sim.step()
        for d in self.attached_displays:
            d.after_step()

    def attach_display(self, display):
        """Attach a display to the control.

        Those displays are updated whenever a step occurs."""
        self.attached_displays.append(display)

    def detach_display(self, display):
        """Detach an attached display from the control."""
        self.attached_displays.remove(display)

    def fullspeed(self):
        """Run the stepping function without any timer delays."""
        last_time = time.time()
        last_step = 0
        while self.isVisible():
            self.step()
            last_step += 1
            QApplication.processEvents()
            if last_step % 1000 == 1:
                diff, last_time = time.time() - last_time, time.time()
                print last_step, diff

class BaseDisplay(QWidget):
    """A base class for different types of displays.

    Manages the config display queue, scrolling, ..."""
    def __init__(self, width, height, queue_size=1, scale=1, **kwargs):
        """Initialize the BaseDisplay.

        :param width: The width of the image to build.
        :param height: The height of the image to build.
        :param queue_size: The amount of histories that may pile up before
                           forcing a redraw.
        """
        super(BaseDisplay, self).__init__(**kwargs)
        self.img_width, self.img_height = width, height
        self.img_scale = scale

        self.resize(self.img_width * self.img_scale,
                    self.img_height * self.img_scale)

        self.create_image_surf()
        self.display_queue = Queue.Queue(queue_size)

        self.last_step = 0
        self.queued_steps = 0

    def create_image_surf(self):
        """Create the image surface when the display is created."""
        self.image = QImage(self.img_width * self.img_scale,
                            self.img_height * self.img_scale,
                            QImage.Format_RGB444)
        self.image.fill(0)

class HistoryDisplay(BaseDisplay):
    """A Display that displays one-dimensional cellular automatons by drawing
    consecutive configurations below each other, wrapping around to the top."""
    def __init__(self, simulator, size, scale=1, **kwargs):
        """:param simulator: The simulator to use.
        :param size: The amount of lines of history to keep before wrapping.
        :param scale: The size of each pixel.
        :param parent: The QWidget to set as parent."""
        super(HistoryDisplay, self).__init__(width=simulator.sizeX,
                      height=size,
                      queue_size=size,
                      scale=scale,
                      **kwargs)
        self.sim = simulator

    def paintEvent(self, ev):
        """Get new configurations, update the internal pixmap, refresh the
        display.

        This is called from Qt whenever a repaint is in order. Do not call it
        yourself. :meth:`after_step` will call update, which will trigger a
        :meth:`paintEvent`.

        .. note::
            In order not to turn into an endless loop, update at most 100
            lines or :attr:`size` lines, whichever is lower."""
        rendered = 0
        y = self.last_step % self.img_height
        w = self.img_width
        scale = self.img_scale
        try:
            painter = QPainter(self.image)
            while rendered < min(100, self.img_height):
                conf = self.display_queue.get_nowait()
                nconf = np.empty((w, 1, 2), np.uint8, "C")
                nconf[...,0,0] = conf * 255
                nconf[...,1] = nconf[...,0]

                image = QImage(nconf.data, w, 1, QImage.Format_RGB444).scaled(w * scale, scale)
                painter.drawImage(QPoint(0, y * scale), image)

                self.queued_steps -= 1
                rendered += 1
                self.last_step += 1
                y = self.last_step % self.img_height
        except Queue.Empty:
            pass
        finally:
            del painter

        copier = QPainter(self)
        copier.drawImage(QPoint(0, 0), self.image)

        del copier


    def after_step(self):
        """React to a single step. Copy the current configuration into the
        :attr:`display_queue` and schedule a call to :meth:`paintEvent`."""
        conf = self.sim.getConf().copy()
        try:
            self.display_queue.put_nowait(conf)
        except Queue.Full:
            # the queue is initialised to hold as much lines as the
            # screen does. if we have more changes queued up than can
            # fit on the screen, we can just skip some of them.
            self.display_queue.get()
            self.display_queue.put(conf)
            # theoretically, in this case, the queued steps var would
            # have to be treated in a special way so that the update
            # line wanders around so that it still works, but
            # since the whole screen will get updated anyway, we
            # don't need to care at all.

        self.queued_steps += 1
        self.update(QRect(
            QPoint(0, ((self.last_step + self.queued_steps - 1) % self.img_height) * self.img_scale),
            QSize(self.img_width * self.img_scale, self.img_scale)))


def main():
    app = QApplication(sys.argv)

    scale = 2
    w, h = 300, 300

    # get a random beautiful CA
    sim = binRule(random.choice(
         [22, 26, 30, 45, 60, 73, 90, 105, 110, 122, 106, 150]),
         w, 0, binRule.INIT_RAND)

    disp = HistoryDisplay(sim, h, scale)
    disp.after_step()

    window = QMainWindow()

    central_widget = QWidget(window)

    window_l = QVBoxLayout(central_widget)

    scroller = QScrollArea()
    window_l.addWidget(scroller)
    scroller.setWidget(disp)
    scroller.resize(800, 600)

    control = Control(sim, parent=central_widget)
    window_l.addWidget(control)
    control.attach_display(disp)

    window.setCentralWidget(central_widget)
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
