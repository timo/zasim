from __future__ import absolute_import

"""This module offers a display and interaction frontend with Qt.

It will try importing PySide first, and if that fails PyQt. The code will
constantly be tested with both bindings."""

from . import cagen
from .simulator import ElementaryCagenSimulator
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
        simulator_menu.addAction("&New...").activated.connect(self.show_new_sim_dlg)
        simulator_menu.addAction("Open &Stepfunc Table").activated.connect(self.open_elementary_tool)
        simulator_menu.addAction("&Quit").activated.connect(self.close)

    def open_elementary_tool(self):
        if self.elementary_tool and not self.elementary_tool.isVisible():
            self.elementary_tool = None
        if self.elementary_tool is None:
            self.elementary_tool = ElementaryRuleWindow(self.sim._step_func.neigh, self.sim.rule_number, parent=self)
            self.elementary_tool.show()

    def show_new_sim_dlg(self):
        try:
            if self.comp_dlg and not self.comp_dlg.isVisible():
                self.comp_dlg = None
        except RuntimeError: # the object on the C++ side had already been deleted
            self.comp_dlg = None
        if self.comp_dlg is None:
            self.comp_dlg = StepFuncCompositionDialog()
            self.comp_dlg.show()

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
                nconf[...,0,0] = conf * 255
                nconf[...,1] = nconf[...,0]

                image = QImage(nconf.data, w, 1, QImage.Format_RGB444).scaled(w * scale, scale)
                painter.drawImage(QPoint(0, y * scale), image)

                self.queued_steps -= 1
                rendered += 1
                if not self.update_no_step:
                    self.last_step += 1
                    y = self.last_step % self.img_height
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

        self.invert_odd = False
        self.odd = False

    def start_inverting_frames(self): self.invert_odd = True
    def stop_inverting_frames(self): self.invert_odd = False

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

class WaitAnimationWindow(object):
    """Display a cute animation, so that the user isn't annoyed by those long,
    long compile times of weave.inline."""
    def __init__(self, **kwargs):
        super(WaitAnimationWindow, self).__init__(**kwargs)

        import pkg_resources as pkg

        scene = QGraphicsScene()

        snake_img = pkg.resource_filename("zasim", "idle.png")
        snake_pic = QImage(snake_img)
        cut_x = 75
        left_part = QPixmap(snake_pic.copy(QRect(QPoint(0, 0), QSize(cut_x, 175))))
        right_part = QPixmap(snake_pic.copy(QRect(QPoint(cut_x, 0), QPoint(175, 175))))

        snake_pos_x = -100
        snake_pos_y = -80
        l_snake = scene.addPixmap(left_part)
        l_snake.setPos(QPoint(snake_pos_x, snake_pos_y))

        numbers_offset = -10

        self.gv = QGraphicsView(scene)
        self.gv.setFixedSize(150, 150)
        self.gv.setSceneRect(QRectF(-75, -75, 150, 150))
        self.gv.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.gv.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        bits = []
        bit_count = 30
        for bit in range(bit_count):
            bitFont = QFont("Monospace", random.randint(8, 16), QFont.Bold, random.choice([True, False]))
            bitBit = QGraphicsTextItem(random.choice("01"))
            bitBit.setFont(bitFont)
            scene.addItem(bitBit)
            x_duration = random.randint(6000, 8000)
            x_anim = QGraphicsItemAnimation()
            x_anim = QPropertyAnimation(bitBit, QByteArray("x"), bitBit)
            x_anim.setDuration(x_duration)
            x_anim.setStartValue(150)
            x_anim.setEndValue(-150)
            x_anim.setLoopCount(-1)
            up_down_duration = random.randint(800, 1200)
            up_down = random.randint(10, 20)
            up_anim = QPropertyAnimation(bitBit, QByteArray("y"), bitBit)
            up_anim.setDuration(up_down_duration)
            up_anim.setStartValue(-up_down + numbers_offset)
            up_anim.setEndValue(up_down + numbers_offset)
            down_anim = QPropertyAnimation(bitBit, QByteArray("y"), bitBit)
            down_anim.setDuration(up_down_duration)
            down_anim.setStartValue(up_down + numbers_offset)
            down_anim.setEndValue(-up_down + numbers_offset)
            up_down_anim = QSequentialAnimationGroup(bitBit)
            up_down_anim.addAnimation(up_anim)
            up_down_anim.addAnimation(down_anim)
            up_down_anim.setLoopCount(-1)

            up_down_anim.start()
            x_anim.start()

            x_anim.setCurrentTime(random.randint(0, x_duration))
            up_down_anim.setCurrentTime(random.randint(0, up_down_duration))

        r_snake = scene.addPixmap(right_part)
        r_snake.setPos(QPoint(snake_pos_x + cut_x, snake_pos_y))

        ct = scene.addSimpleText("Compiling")
        ct.setFont(QFont("Monospace", 12))
        ct.translate(-ct.boundingRect().width()/2., 75 - ct.boundingRect().height())

        self.gv.centerOn(0, 0)

        self.scene = scene
        self.gv.show()

    def destroy(self):
        self.gv.deleteLater()

class StepFuncCompositionDialog(QWidget):
    """With this dialog, the user can, by selecting classes from a categorized
    tree of classes derived from WeaveStepFuncVisitor, assemble a step
    function.

    In a later version, the user will also be able to set arguments, such as
    the probability for nondeterministic visitors."""

    single_categories = ["loop", "accessor", "neighbourhood"]
    """The categories that can hold only a single class.

    These correspond closely to the keyword arguments of
    :meth:`WeaveStepFunc.__init__` with the same name."""

    def __init__(self, **kwargs):
        super(StepFuncCompositionDialog, self).__init__(**kwargs)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self.parts = {}
        self.extraparts = []

        self.setup_ui()
        self.part_tree.currentItemChanged.connect(self.update_docs)
        self.part_tree.itemDoubleClicked.connect(self.dbl_click_item)

        self.cancel_button.clicked.connect(self.close)
        self.create_button.clicked.connect(self.create)

    def update_docs(self, new, old):
        """Display the docstring of the class and its __init__ at the bottom of
        the window when a new class has been selected, or display a general
        help text when the user clicks on something else."""

        obj = new.data(0, CLASS_OBJECT_ROLE)
        if obj is None:
            data = """<h2>Create a stepfunction from parts</h2>

Doubleclick on classes from the list on the left to set them at the right, or
click on the buttons on the right to remove classes again.

Doubleclick on items in the right list of extra classes to remove them.

This pane at the bottom will display documentation."""

        else:
            data = """<h2>%s</h2>
%s""" % (obj.__name__, obj.__doc__)
            try:
                if get_class_for_implementation(obj.__init__) == obj:
                    data += """<h2>Constructor</h2>
    %s""" % (obj.__init__.__doc__)
            except AttributeError:
                pass
        self.doc_display.setText(data)

    def setup_ui(self):
        categories = cagen.categories()

        outermost_layout = QVBoxLayout(self)

        outer_layout = QSplitter(Qt.Vertical, self)
        outermost_layout.addWidget(outer_layout)

        # upper part: list and slots
        upper_widget = QWidget(self)
        upper_pane = QHBoxLayout(upper_widget)
        upper_widget.setLayout(upper_pane)
        outer_layout.addWidget(upper_widget)

        # left pane: list of all available parts
        left_pane = QVBoxLayout()
        self.part_tree = QTreeWidget(upper_widget)
        self.part_tree.setHeaderHidden(True)
        left_pane.addWidget(self.part_tree)

        for (category, classes) in categories.iteritems():
            cat_item = QTreeWidgetItem([category])

            for cls in classes:
                cls_item = QTreeWidgetItem([cls.__name__])
                cls_item.setData(0, CLASS_OBJECT_ROLE, cls)
                cat_item.addChild(cls_item)

            self.part_tree.addTopLevelItem(cat_item)
            self.part_tree.expandItem(cat_item)

        # right pane: selected parts
        right_pane = QGridLayout()
        self.category_buttons = {}
        for num, category in enumerate(self.single_categories):
            label = QLabel(category, self)
            slot = QPushButton(self)
            right_pane.addWidget(label, num, 0)
            right_pane.addWidget(slot, num, 1)
            self.category_buttons[category] = slot
        num += 1
        label = QLabel("additionals", self)
        self.additional_list = QListWidget(self)
        right_pane.addWidget(label, num, 0, 1, 2)
        right_pane.addWidget(self.additional_list, num + 1, 0, 1, 2)

        # lower part: documentation
        self.doc_display = QTextEdit(self)
        self.doc_display.setReadOnly(True)

        outer_layout.addWidget(self.doc_display)

        upper_pane.addLayout(left_pane)
        upper_pane.addLayout(right_pane)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel", self)
        self.create_button = QPushButton("Create", self)

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.create_button)

        outermost_layout.addLayout(button_layout)
        self.setLayout(outermost_layout)

    def dbl_click_item(self, item, column):
        """When the user activates a class in the list, insert it into the
        correct slot at the right."""

        cls = item.data(0, CLASS_OBJECT_ROLE)
        if cls.category in self.single_categories:
            button = self.category_buttons[cls.category]
            button.setText(cls.__name__)
            self.parts[cls.category] = cls
        else:
            self.additional_list.addItem(cls.__name__)
            self.extraparts.append(cls)

    def create(self):
        extra_code = "[%s]" % (", ".join(
            ["%s()" % (cls.__name__) for cls in self.extraparts]))
        generated_code = """
w, h = 200, 200
scale = 3

t = cagen.TestTarget(size=(w, h))
l = %(loop)s()
acc = %(acc)s()
neigh = %(neigh)s()
extra_code = %(extra)s
sim = cagen.WeaveStepFunc(loop=l, accessor=acc, neighbourhood=neigh,
                extra_code=[extra_code], target=t)

sim.gen_code()

sim_obj = ElementaryCagenSimulator(sim, t)

display_obj = ZasimDisplay(sim_obj)
display_obj.set_scale(scale)
display_objects.append(display_obj)

display_obj.control.start()""" % dict(
            loop=self.parts["loop"].__name__, acc=self.parts["accessor"].__name__,
            neigh=self.parts["neighbourhood"].__name__, extra=extra_code)

        EditWindow(generated_code).exec_()

class EditWindow(QDialog):
    def __init__(self, code, title="Editing code"):
        super(EditWindow, self).__init__()
        self.setWindowTitle(title)
        self.setup_ui()
        self.edit_widget.setText(code)

        self.run_button.clicked.connect(self.run_code)
        self.cancel_button.clicked.connect(self.rejected)

    def setup_ui(self):
        l = QVBoxLayout(self)
        self.edit_widget = QTextEdit(self)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.run_button = QPushButton("Execute")
        self.cancel_button = QPushButton("Cancel")

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.run_button)

        l.addWidget(self.edit_widget)
        l.addLayout(button_layout)

        self.setLayout(l)

    def run_code(self):
        exec self.edit_widget.toPlainText() in globals(), locals()
        self.accepted.emit()
        self.close()

def main(rule=None):
    app = QApplication(sys.argv)

    scale = 3
    w, h = 200, 200

    onedim, twodim = False, True
    beta = False
    nondet = True

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

        if rule is not None:
            rule_number = rule
        else:
            rule_number = random.randint(0, 2 ** 32)

        compute = cagen.ElementaryCellularAutomatonBase(rule=rule_number)
        t.rule_number = rule_number # XXX this must be better.


        if beta or not nondet:
            l = cagen.TwoDimCellLoop()
        elif nondet:
            l = cagen.TwoDimNondeterministicCellLoop(probab=0.7)
        if beta:
            acc = cagen.BetaAsynchronousAccessor()
            neigh = cagen.VonNeumannNeighbourhood(Base=cagen.BetaAsynchronousNeighbourhood)
        else:
            acc = cagen.SimpleStateAccessor()
            neigh = cagen.VonNeumannNeighbourhood()
        copier = cagen.TwoDimSlicingBorderCopier()
        hist = cagen.SimpleHistogram()
        activity = cagen.ActivityRecord()
        sim = cagen.WeaveStepFunc(loop=l, accessor=acc, neighbourhood=neigh,
                        extra_code=[copier, compute, hist, activity], target=t)

        sim.gen_code()
        print compute.pretty_print()
        print compute.rule, hex(compute.rule)

        sim_obj = ElementaryCagenSimulator(sim, t)

        display_b = ZasimDisplay(sim_obj)
        display_b.set_scale(scale)
        display_objects.append(display_b)

        display_b.control.start()

        extra_hist = HistogramExtraDisplay(sim_obj, parent=display_b, height=200, maximum= w * h)
        extra_activity = HistogramExtraDisplay(sim_obj, attribute="activity", parent=display_b, height=200, maximum=w*h)

        extra_hist.show()
        extra_activity.show()


        display_b.window.attach_display(extra_hist)
        display_b.window.attach_display(extra_activity)

        display_b.window.addDockWidget(Qt.RightDockWidgetArea, extra_hist)
        display_b.window.addDockWidget(Qt.RightDockWidgetArea, extra_activity)

    #comp_dlg = StepFuncCompositionDialog()
    #comp_dlg.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1].startswith("0x"):
            rule_nr = int(sys.argv[1], 16)
        else:
            rule_nr = int(sys.argv[1])
        main(rule_nr)
    else:
        main()
