from __future__ import absolute_import

"""This module offers a display and interaction frontend with Qt.

It will try importing PySide first, and if that fails PyQt. The code will
constantly be tested with both bindings."""

from . import cagen
from .simulator import CagenSimulator

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
from itertools import product
import numpy as np

class ZasimDisplay(object):
    def __init__(self, simulator):#, display_widget=None, main_window=None, control_widget=None):
        """Instantiate a Display (thas is: a window with a display widget and
        simulation controls) from a simulator.

        :param simulator: The simulator to use.
        #:param display_widget: The display widget to use. If None is supplied,
                               #a matching one will be created.
        #:param main_window: The :class:`ZasimMainWindow` instance to use, if no
                            #new instance should be created.
        #:param control_widget: The :class:`ontrolWidget` instance to use, if no
                               #new instance should be created."""

        self.simulator = simulator
        self.display = None # display_widget
        self.window = None #main_window
        self.control = None #control_widget

        if not self.display:
            if len(simulator.shape) == 1:
                self.display = HistoryDisplayWidget(self.simulator,
                            self.simulator.shape[0])
            elif len(simulator.shape) == 2:
                self.display = TwoDimDisplayWidget(self.simulator)
            else:
                raise ValueError("Unsupported shape size: %d" % len(simulator.shape))

        if self.control is None:
            self.control = ControlWidget(self.simulator)

        if self.window is None:
            self.window = ZasimMainWindow(self.simulator, self.display, self.control)
        self.window.show()

    def set_scale(self, scale):
        """Sets the scale of the display component."""
        self.display.set_scale(scale)

class ZasimMainWindow(QMainWindow):
    """This is a window that manages one simulator. It holds one
    :class:`Control`, at least one :class:`BaseDisplayWidget` and any number of
    additional views embedded in QDockWidgets."""

    control = None
    """The control widget responsible for this window."""

    simulator = None
    """The simulator that is controlled in this window."""

    display = None
    """The main display for the simulator."""

    extra_displays = []
    """Additional displays in docks."""


    display_attached = Signal(["BaseDisplayWidget"])
    """Emitted when a new display has been attached"""

    display_detached = Signal(["BaseDisplayWidget"])
    """Emitted when a display has been detached"""

    def __init__(self, simulator, display, control=None, **kwargs):
        """Sets up this window with a simulator, a display and optionally a
        control widget.

        :param simulator: The simulator object to use.
        :param display: A :class:`BaseDisplayWidget` instance.
        :param control: Optionally, a :class:`ControlWidget` instance."""
        super(ZasimMainWindow, self).__init__(**kwargs)
        self.simulator = simulator
        self.display = display
        self.control = control

        central_widget = QWidget(self)

        if self.control is None:
            self.control = ControlWidget(self.simulator, parent=central_widget)

        layout = QVBoxLayout(central_widget)

        scroller = QScrollArea()
        scroller.setWidget(self.display)

        layout.addWidget(scroller)
        layout.addWidget(self.control)

        self.setCentralWidget(central_widget)

        self.simulator.updated.connect(self.display.after_step)

    def attach_display(self, display):
        """Attach an extra display to the control.

        Those displays are updated whenever a step occurs."""
        self.attached_displays.append(display)
        self.display_attached.emit(display)

    def detach_display(self, display):
        """Detach an extra attached display from the control."""
        self.attached_displays.remove(display)
        self.display_detached.emit(display)

class ControlWidget(QWidget):
    """Control a simulator with buttons or from the interactive console."""

    def __init__(self, simulator, **kwargs):
        """:param simulator: The simulator object to control."""
        super(ControlWidget, self).__init__(**kwargs)

        self.sim = simulator
        self.timer_delay = 0

        self._setup_ui()

    def _setup_ui(self):
        """Setup the widgets, connect the signals&slots."""
        l = QHBoxLayout(self)
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setDisabled(True)
        delay = QSpinBox()
        delay.setMinimum(0)
        delay.setMaximum(10000)
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

class BaseDisplayWidget(QWidget):
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


class HistoryDisplayWidget(BaseDisplayWidget):
    """A Display that displays one-dimensional cellular automatons by drawing
    consecutive configurations below each other, wrapping around to the top."""
    def __init__(self, simulator, height, scale=1, **kwargs):
        """:param simulator: The simulator to use.
        :param height: The amount of lines of history to keep before wrapping.
        :param scale: The size of each pixel.
        :param parent: The QWidget to set as parent."""
        super(HistoryDisplayWidget, self).__init__(width=simulator.shape[0],
                      height=height,
                      queue_size=height,
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

        copier = QPainter(self)
        copier.drawImage(QPoint(0, 0), self.image)


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

class TwoDimDisplayWidget(BaseDisplayWidget):
    def __init__(self, simulator, scale=1, **kwargs):
        super(TwoDimDisplayWidget, self).__init__(width=simulator.shape[0],
                    height=simulator.shape[1],
                    queue_size=1,
                    scale=scale,
                    **kwargs)

        self.sim = simulator
        self.conf_new = True
        self.queued_conf = simulator.getConf()

    def paintEvent(self, ev):
        """Get new configurations, update the internal pixmap, refresh the
        display.

        This is called from Qt whenever a repaint is in order. Do not call it
        yourself. :meth:`after_step` will call update, which will trigger a
        :meth:`paintEvent`.

        .. note::
            Only the very latest config will be displayed. All others will be
            dropped immediately."""
        if self.conf_new:
            conf = self.queued_conf
            self.conf_new = False
            w, h = conf.shape
            nconf = np.empty((w, h, 2), np.uint8, "C")
            nconf[...,0] = conf * 255
            nconf[...,1] = nconf[...,0]
            self.image = QImage(nconf.data, w, h, QImage.Format_RGB444).scaled(
                    w * self.img_scale, h * self.img_scale)

        copier = QPainter(self)
        copier.drawImage(QPoint(0, 0), self.image)
        del copier

    def after_step(self):
        """React to a single step. Set the :attr:`queued_conf` to a copy of the
        current config and trigger a :meth:`paintEvent`."""
        conf = self.sim.getConf().copy()
        self.queued_conf = conf
        self.conf_new = True

        self.update()

def display_for(simulator):
    si

def main():
    app = QApplication(sys.argv)

    scale = 2
    w, h = 300, 300

    onedim, twodim = True, True

    if onedim:
        # get a random beautiful CA
        sim = cagen.BinRule(rule=random.choice(
             [22, 26, 30, 45, 60, 73, 90, 105, 110, 122, 106, 150]),
             size=(w,))

        sim_obj = CagenSimulator(sim.stepfunc, sim)
        display_a = ZasimDisplay(sim_obj)
        display_a.set_scale(scale)

    if twodim:
        twodim_rand = np.zeros((w, h), int)
        for x, y in product(range(w), range(h)):
            twodim_rand[x, y] = random.choice([0, 0, 0, 1])

        t = cagen.TestTarget(config=twodim_rand)

        compute = cagen.LifeCellularAutomatonBase()
        l = cagen.TwoDimNondeterministicCellLoop(probab=0.4)
        acc = cagen.TwoDimStateAccessor()
        neigh = cagen.MooreNeighbourhood()
        copier = cagen.SimpleBorderCopier()
        #copier = cagen.TwoDimZeroReader()
        sim = cagen.WeaveStepFunc(loop=l, accessor=acc, neighbourhood=neigh,
                        extra_code=[copier, compute], target=t)

        sim.gen_code()

        sim_obj = CagenSimulator(sim, t)

        display_b = ZasimDisplay(sim_obj)
        display_b.set_scale(scale)

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
