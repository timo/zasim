from __future__ import absolute_import

"""This module offers a display and interaction frontend with Qt.

It will try importing PySide first, and if that fails PyQt. The code will
constantly be tested with both bindings."""

from . import cagen
from .simulator import ElementaryCagenSimulator, CagenSimulator
from .elementarygui import ElementaryRuleWindow

try:
    from PySide.QtCore import *
    from PySide.QtGui import *
    try:
        from PySide.QtOpenGL import *
    except ImportError:
        QGLWidget = QWidget
    print "using pyside"
except ImportError:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    try:
        from PyQt4.QtOpenGL import *
    except ImportError:
        QGLWidget = QWidget
    print "using pyqt4"
import Queue
import sys
import random
import time
from itertools import product
import numpy as np

import inspect

def get_class_for_implementation(meth):
    """Taken from stackoverflow user Alex Martelli."""
    for cls in inspect.getmro(meth.im_class):
        if meth.__name__ in cls.__dict__: return cls
    return None

CLASS_OBJECT_ROLE = Qt.UserRole + 1

display_objects = []

class ZasimDisplay(object):

    simulator = None
    """The :class:`Simulator` object for this display."""

    display = None
    """The :class:`BaseDisplayWidget` in use."""

    window = None
    """The :class:`ZasimMainWindow` instance in use."""

    control = None
    """The :class:`ControlWidget` in use."""

    def __init__(self, simulator):#, display_widget=None, main_window=None, control_widget=None):
        """Instantiate a Display (thas is: a window with a display widget and
        simulation controls) from a simulator.

        :param simulator: The simulator to use."""

        self.simulator = simulator

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

        self.setAttribute(Qt.WA_DeleteOnClose)

        self.simulator = simulator
        self.display = display
        self.control = control

        central_widget = QWidget(self)

        if self.control is None:
            self.control = ControlWidget(self.simulator, parent=central_widget)

        layout = QVBoxLayout(central_widget)

        layout.addWidget(QLabel(str(self.simulator), self))

        scroller = QScrollArea()
        scroller.setWidget(self.display)

        layout.addWidget(scroller)
        layout.addWidget(self.control)

        self.setCentralWidget(central_widget)

        self.simulator.updated.connect(self.display.after_step)
        self.simulator.changed.connect(self.display.conf_changed)

        self.control.start_inverting_frames.connect(self.display.start_inverting_frames)
        self.control.stop_inverting_frames.connect(self.display.stop_inverting_frames)

        self.setup_menu()

        self.elementary_tool = None
        self.comp_dlg = None

    def setup_menu(self):
        simulator_menu = self.menuBar().addMenu("Simulator")
        simulator_menu.addAction("Open &Stepfunc Table").activated.connect(self.open_elementary_tool)
        simulator_menu.addAction("&Quit").activated.connect(self.close)

    def open_elementary_tool(self):
        if self.elementary_tool and not self.elementary_tool.isVisible():
            self.elementary_tool = None
        if self.elementary_tool is None:
            self.elementary_tool = ElementaryRuleWindow(self.simulator._step_func.neigh, self.simulator.rule_number)
            self.elementary_tool.show()

    def attach_display(self, display):
        """Attach an extra display to the control.

        Those displays are updated whenever a step occurs."""
        self.extra_displays.append(display)
        self.simulator.updated.connect(display.after_step)
        self.simulator.changed.connect(display.conf_changed)
        #self.display_attached.emit(display)

    def detach_display(self, display):
        """Detach an extra attached display from the control."""
        self.extra_displays.remove(display)
        self.simulator.updated.disconnect(display.after_step)
        self.simulator.changed.disconnect(display.conf_changed)
        #self.display_detached.emit(display)

class ControlWidget(QWidget):
    """Control a simulator with buttons or from the interactive console."""

    start_inverting_frames = Signal()
    stop_inverting_frames = Signal()

    def __init__(self, simulator, **kwargs):
        """:param simulator: The simulator object to control."""
        super(ControlWidget, self).__init__(**kwargs)

        self.sim = simulator
        self.timer_delay = 0

        self._setup_ui()

    def _setup_ui(self):
        """Setup the widgets, connect the signals&slots."""
        l = QHBoxLayout(self)
        self.start_button = QPushButton("&Start", self)
        self.stop_button = QPushButton("&Stop", self)
        self.stop_button.hide()
        delay = QSpinBox()
        delay.setMinimum(0)
        delay.setMaximum(10000)
        delay.setSuffix(" ms")
        delay.setValue(self.timer_delay)

        l.addWidget(self.start_button)
        l.addWidget(self.stop_button)
        l.addWidget(delay)

        l.addSpacing(11)
        reset_button = QPushButton("&reset", self)
        reset_button.clicked.connect(self.set_config)
        l.addWidget(reset_button)

        self.zero_percentage = QSpinBox(self)
        self.zero_percentage.setMaximum(99)
        self.zero_percentage.setMinimum(1)
        self.zero_percentage.setValue(50)
        self.zero_percentage.setSuffix("% black")
        l.addWidget(self.zero_percentage)

        self.invert_frames = QCheckBox(self)
        self.invert_frames.setChecked(False)
        self.invert_frames.setText("&invert odd frames")
        self.invert_frames.stateChanged.connect(self.invert_odd)
        l.addWidget(self.invert_frames)

        self.setLayout(l)

        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        delay.valueChanged.connect(self.change_delay)

    def invert_odd(self, value):
        if value == Qt.Checked:
            self.start_inverting_frames.emit()
        else:
            self.stop_inverting_frames.emit()

    def start(self):
        """Start running the simulator."""
        self.timer_id = self.startTimer(self.timer_delay)
        self.start_button.hide()
        self.stop_button.show()

    def stop(self):
        """Stop the simulator."""
        self.killTimer(self.timer_id)
        self.stop_button.hide()
        self.start_button.show()

    def change_delay(self, delay):
        """Change the timer delay of the simulator steps."""
        if delay.endswith("ms"):
            delay = delay[:-2]
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

    def set_config(self, conf=None):
        if conf is None:
            conf = np.zeros(self.sim.get_config().shape, self.sim.get_config().dtype)
            positions = product(*[range(size) for size in conf.shape])
            zero_perc = self.zero_percentage.value() / 100.
            for pos in positions:
                if random.random() > zero_perc:
                    conf[pos] = 1

        self.sim.set_config(conf)

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
        self.update_no_step = False

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
                if not self.invert_odd or self.odd:
                    nconf[...,0,0] = conf * 255
                else:
                    nconf[...,0,0] = (1 - conf) * 255
                nconf[...,1] = nconf[...,0]

                image = QImage(nconf.data, w, 1, QImage.Format_RGB444).scaled(w * scale, scale)
                painter.drawImage(QPoint(0, y * scale), image)

                self.queued_steps -= 1
                rendered += 1
                if not self.update_no_step:
                    self.last_step += 1
                    y = self.last_step % self.img_height
                    self.odd = not self.odd
                else:
                    self.update_no_step = False
        except Queue.Empty:
            pass

        copier = QPainter(self)
        copier.drawImage(QPoint(0, 0), self.image)

    def after_step(self):
        """React to a single step. Copy the current configuration into the
        :attr:`display_queue` and schedule a call to :meth:`paintEvent`."""
        conf = self.sim.get_config().copy()
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

    def conf_changed(self):
        """React to a change in the configuration that was not caused by a step
        of the cellular automaton - by a user interaction for instance."""
        self.after_step()
        self.update_no_step = True

class TwoDimDisplayWidget(BaseDisplayWidget):
    """A display widget for two-dimensional configurations."""
    def __init__(self, simulator, scale=1, **kwargs):
        super(TwoDimDisplayWidget, self).__init__(width=simulator.shape[0],
                    height=simulator.shape[1],
                    queue_size=1,
                    scale=scale,
                    **kwargs)

        self.sim = simulator
        self.conf_new = True
        self.queued_conf = simulator.get_config()

        self.drawing = False
        self.last_draw_pos = QPoint(0,0)


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
            if not self.invert_odd or self.odd:
                nconf[...,0] = conf * 255
            else:
                nconf[...,0] = 255 - conf * 255
            nconf[...,1] = nconf[...,0]
            self.image = QImage(nconf.data, w, h, QImage.Format_RGB444).scaled(
                    w * self.img_scale, h * self.img_scale)
            self.odd = not self.odd

        copier = QPainter(self)
        copier.drawImage(QPoint(0, 0), self.image)
        del copier

    def after_step(self):
        """React to a single step. Set the :attr:`queued_conf` to a copy of the
        current config and trigger a :meth:`paintEvent`."""
        conf = self.sim.get_config().copy()
        self.queued_conf = conf
        self.conf_new = True

        self.update()

    def conf_changed(self):
        self.after_step()

    def mousePressEvent(self, event):
        self.drawing = True
        self.last_draw_pos = (event.x() / self.img_scale, event.y() / self.img_scale)

    def mouseReleaseEvent(self, event):
        self.drawing = False

    def leaveEvent(self, event):
        self.drawing = False

    def mouseMoveEvent(self, event):
        new_draw_pos = (event.x() / self.img_scale, event.y() / self.img_scale)
        if self.last_draw_pos != new_draw_pos:
            self.sim.set_config_value(new_draw_pos)

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

class HistogramExtraDisplay(BaseExtraDisplay):
    """This extra display can take any attribute from the simulation target
    that is an one-dimensional array and display its values over time as
    colored vertical lines."""
    colors = [QColor("black"), QColor("white"), QColor("red"), QColor("blue"),
              QColor("green"), QColor("yellow")]
    def __init__(self, sim, attribute="histogram", width=400, maximum=1.0, **kwargs):
        super(HistogramExtraDisplay, self).__init__(title=attribute, sim=sim, width=width, **kwargs)
        self.linepos = 0
        self.queue = Queue.Queue(width)
        self.attribute = attribute
        self.update_no_step = False

    def paint_display_widget(self, event):
        painter = QPainter(self.image)
        linepos = self.linepos
        try:
            while True:
                values = self.queue.get_nowait()
                maximum = sum(values)
                scale = self.img_height * 1.0 / maximum
                absolute = 0.0
                for value, color in zip(values, self.colors):
                    value = value * scale
                    painter.setPen(color)
                    painter.drawLine(QLine(linepos, absolute,
                                     linepos, absolute + value))
                    absolute += value

                if not self.update_no_step:
                    linepos += 1
                    if linepos >= self.width():
                        linepos = 0

        except Queue.Empty:
            pass

        copier = QPainter(self.display_widget)
        copier.drawImage(QPoint(0, 0), self.image)
        del copier
        self.linepos = linepos

    def after_step(self):
        value = getattr(self.sim._target, self.attribute).copy()
        try:
            self.queue.put_nowait(value)
        except Queue.Full:
            self.queue.get()
            self.queue.put(value)

        self.update_no_step = False
        self.display_widget.update()

    def conf_changed(self):
        self.after_step()
        self.update_no_step = True

def main(width=200, height=200, scale=2,
        onedim=False,
        beta=100, nondet=100,
        life=False, rule=None,
        copy_borders=True, white=50,
        histogram=True, activity=True):
    app = QApplication(sys.argv)

    if white > 1:
        white = white / 100.

    beta = beta / 100.
    nondet = nondet / 100.

    w, h = width, height

    if onedim and not life:
        onedim_rand = np.zeros((w,), int)
        for x in range(w):
            onedim_rand[x] = int(random.random() < white)

        # get a random beautiful CA
        if rule is None:
            rule=random.choice(
             [22, 26, 30, 45, 60, 73, 90, 105, 110, 122, 106, 150])

        sim = cagen.BinRule(rule=rule, size=(w,), nondet=nondet, beta=beta, activity=activity,
                histogram=histogram, copy_borders=copy_borders)

        sim_obj = ElementaryCagenSimulator(sim.stepfunc, sim)

    else:
        twodim_rand = np.zeros((w, h), int)
        for x, y in product(range(w), range(h)):
            twodim_rand[x, y] = int(random.random() < white)

        t = cagen.TestTarget(config=twodim_rand)

        if life:
            compute = cagen.LifeCellularAutomatonBase()
            NeighClass = cagen.MooreNeighbourhood
        else:
            NeighClass = cagen.VonNeumannNeighbourhood
            if rule is not None:
                rule_number = rule
            else:
                rule_number = random.randint(0, 2 ** 32)

            compute = cagen.ElementaryCellularAutomatonBase(rule=rule_number)
            t.rule_number = rule_number # XXX this must be better.


        if beta != 1 or nondet == 1:
            l = cagen.TwoDimCellLoop()
        elif nondet != 1:
            l = cagen.TwoDimNondeterministicCellLoop(probab=nondet)

        if beta != 1:
            acc = cagen.BetaAsynchronousAccessor(probab=0.1)
            neigh = NeighClass(Base=cagen.BetaAsynchronousNeighbourhood)
        else:
            acc = cagen.SimpleStateAccessor()
            neigh = NeighClass()

        extra_code = [compute]
        extra_code.append(cagen.TwoDimSlicingBorderCopier() if copy_borders else
                cagen.TwoDimZeroReader())
        if histogram:
            extra_code.append(cagen.SimpleHistogram())
        if activity:
            extra_code.append(cagen.ActivityRecord())
        sim = cagen.WeaveStepFunc(loop=l, accessor=acc, neighbourhood=neigh,
                        extra_code=extra_code, target=t)

        sim.gen_code()

        if not life:
            print compute.pretty_print()
            print compute.rule, hex(compute.rule)

            sim_obj = ElementaryCagenSimulator(sim, t)
        else:
            sim_obj = CagenSimulator(sim, t)

    display = ZasimDisplay(sim_obj)
    display.set_scale(scale)
    display_objects.append(display)

    display.control.start()

    if histogram:
        extra_hist = HistogramExtraDisplay(sim_obj, parent=display, height=200, maximum= w * h)
        extra_hist.show()
        display.window.attach_display(extra_hist)
        display.window.addDockWidget(Qt.RightDockWidgetArea, extra_hist)

    if activity:
        extra_activity = HistogramExtraDisplay(sim_obj, attribute="activity", parent=display, height=200, maximum=w*h)
        extra_activity.show()
        display.window.attach_display(extra_activity)
        display.window.addDockWidget(Qt.RightDockWidgetArea, extra_activity)

    sys.exit(app.exec_())

if __name__ == "__main__":
    import argparse

    argp = argparse.ArgumentParser(
        description="Run a 1d BinRule, a 2d Game of Life, or a 2d elementary "
                    "cellular automaton")
    argp.add_argument("--onedim", default=False, action="store_true",
            help="generate a one-dimensional cellular automaton")
    argp.add_argument("--twodim", default=True, action="store_false", dest="onedim",
            help="generate a two-dimensional cellular automaton")
    argp.add_argument("--life", default=False, action="store_true",
            help="generate a conway's game of life - implies --twodim")

    argp.add_argument("-x", "--width", default=200, dest="width", type=int,
            help="the width of the image surface")
    argp.add_argument("-y", "--height", default=200, dest="height", type=int,
            help="the height of the image surface")
    argp.add_argument("-z", "--scale", default=3, dest="scale", type=int,
            help="the size of each cell of the configuration")
    argp.add_argument("-r", "--rule", default=None, type=int,
            help="the elementary cellular automaton rule number to use")
    argp.add_argument("-c", "--dont-copy-borders", default=True, action="store_false", dest="copy_borders",
            help="copy borders or just read zeros?")
    argp.add_argument("--white", default=20, type=int,
            help="what percentage of the cells to make white at the beginning.")

    argp.add_argument("--nondet", default=100, type=int,
            help="with what percentage should cells be executed?")
    argp.add_argument("--beta", default=100, type=int,
            help="with what probability should a cell succeed in exposing its "\
                 "state to its neighbours?")

    argp.add_argument("--no-histogram", default=True, action="store_false", dest="histogram",
            help="don't display a histogram")
    argp.add_argument("--no-activity", default=True, action="store_false", dest="activity",
            help="don't display the activity")

    args = argp.parse_args()

    main(**vars(args))


    if len(sys.argv) > 1:
        if sys.argv[1].startswith("0x"):
            rule_nr = int(sys.argv[1], 16)
        else:
            rule_nr = int(sys.argv[1])
        main(rule_nr)
    else:
        main()
