from ..external.qt import (QMainWindow, QDialog, Signal, QWidget, QVBoxLayout, QScrollArea,
        QLabel, Qt)
from .. import cagen
from ..simulator import CagenSimulator
from .display import ZasimDisplay
from .histogram import HistogramExtraDisplay
from .control import ControlWidget
from .elementary import ElementaryRuleWindow
from .externaledit import ExternalEditWindow
from .argp_qt import NewZasimWindow
from .reset import ResetDocklet

import numpy as np

class ZasimMainWindow(QMainWindow):
    """This is a window that manages one simulator. It holds one
    `Control`, at least one `DisplayWidget` and any number of
    additional views embedded in QDockWidgets."""

    control = None
    """The control widget responsible for this window."""

    simulator = None
    """The simulator that is controlled in this window."""

    display = None
    """The main display for the simulator."""

    extra_displays = []
    """Additional displays in docks."""


    display_attached = Signal(["DisplayWidget"])
    """Emitted when a new display has been attached"""

    display_detached = Signal(["DisplayWidget"])
    """Emitted when a display has been detached"""

    def __init__(self, simulator, display, control=None, **kwargs):
        """Sets up this window with a simulator, a display and optionally a
        control widget.

        :param simulator: The simulator object to use.
        :param display: A `DisplayWidget` instance.
        :param control: Optionally, a `ControlWidget` instance."""
        super(ZasimMainWindow, self).__init__(**kwargs)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self.simulator = simulator
        self.display = display
        self.control = control

        central_widget = QWidget(self)

        if self.control is None:
            self.control = ControlWidget(self.simulator, parent=central_widget)

        layout = QVBoxLayout(central_widget)

        sim_name = QLabel(str(self.simulator), self)
        # make text selectable and links (if any) clickable
        sim_name.setTextInteractionFlags(Qt.TextBrowserInteraction)
        # there are some nasty long names if base gets bigger than 2.
        sim_name.setWordWrap(True)

        layout.addWidget(sim_name)

        scroller = QScrollArea()
        scroller.setWidget(self.display)

        layout.addWidget(scroller)
        layout.addWidget(self.control)
        self.control.setObjectName("control")

        self.setCentralWidget(central_widget)

        self.setup_menu()

        self.elementary_tool = None
        #self.comp_dlg = None
        self.new_dlg = None

        self.resetter = ResetDocklet(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.resetter)

    def setup_menu(self):
        simulator_menu = self.menuBar().addMenu("Simulator")
        simulator_menu.setObjectName("simulator_menu")

        new_a = simulator_menu.addAction("&New...")
        new_a.setObjectName("new")
        new_a.activated.connect(self.show_new_sim_dlg)

        stepf_a = simulator_menu.addAction("Open &Stepfunc Table")
        stepf_a.setObjectName("stepfunc_table")
        stepf_a.activated.connect(self.open_elementary_tool)

        ext_img_a = simulator_menu.addAction("Edit image")
        ext_img_a.setObjectName("external_image")
        ext_img_a.activated.connect(self.open_external_img)

        ext_img_a = simulator_menu.addAction("Edit ascii-art")
        ext_img_a.setObjectName("external_text")
        ext_img_a.activated.connect(self.open_external_txt)

        quit_a = simulator_menu.addAction("&Quit")
        quit_a.setObjectName("quit")
        quit_a.activated.connect(self.close)

    def open_external_img(self):
        editwin = ExternalEditWindow(self.simulator)
        editwin.external_png()

    def open_external_txt(self):
        editwin = ExternalEditWindow(self.simulator)
        editwin.external_txt()

    def open_elementary_tool(self):
        if self.elementary_tool and not self.elementary_tool.isVisible():
            self.elementary_tool = None
        if self.elementary_tool is None:
            self.elementary_tool = ElementaryRuleWindow(self.simulator._step_func.neigh, self.simulator.rule_number, base=len(self.simulator.t.possible_values))
            self.elementary_tool.setObjectName("elementary_tool")
            self.elementary_tool.show()

    def show_new_sim_dlg(self):
        self.new_dlg = NewZasimWindow()
        self.new_dlg.setObjectName("new_dialog")

        if QDialog.Accepted == self.new_dlg.exec_():
            main(**vars(self.new_dlg.args))

    def attach_display(self, display):
        """Attach an extra display to the control.

        Those displays are updated whenever a step occurs."""
        self.extra_displays.append(display)
        self.addDockWidget(Qt.RightDockWidgetArea, display)
        #self.display_attached.emit(display)

    def detach_display(self, display):
        """Detach an extra attached display from the control."""
        self.extra_displays.remove(display)
        self.removeDockWidget(display)
        #self.display_detached.emit(display)

def main(width=200, height=200, scale=2,
        onedim=False,
        beta=100, nondet=100,
        life=False, rule=None, alt_rule=None,
        copy_borders=True, black=None,
        no_histogram=False, no_activity=False,
        base=2, sparse=False):

    # this makes argp_qt more happy
    histogram = not no_histogram
    activity = not no_activity

    if beta > 1:
        beta = beta / 100.
    if nondet > 1:
        nondet = nondet / 100.
    if black > 2:
        black = black / 100

    w, h = width, height
    if onedim:
        size = (w,)
    else:
        size = w, h

    if black is not None:
        rands = np.random.rand(*size)
        config = np.random.randint(0, base, size)
        config[rands < black] = 0

        size = None
    else:
        config = None

    print size, config

    if onedim and not life:
        if alt_rule is None:
            # get a random beautiful CA
            sim_obj = cagen.BinRule(rule=rule, size=size, config=config, nondet=nondet, beta=beta, activity=activity,
                    histogram=histogram, copy_borders=copy_borders, base=base, sparse_loop=sparse)
        else:
            alt_rule = None if alt_rule == -1 else alt_rule
            compu = cagen.DualRuleCellularAutomaton(rule, alt_rule, nondet)
            sf_obj = cagen.automatic_stepfunc(size=size, config=config,
                    computation=compu, histogram=histogram, activity=activity,
                    copy_borders=copy_borders, base=base,
                    needs_random_generator=True)
            sf_obj.gen_code()
            print compu.pretty_print()
            print compu.rule_a, compu.rule_b
            sim_obj = CagenSimulator(sf_obj, sf_obj.target)

    else:
        if life:
            sim_obj = cagen.GameOfLife(size, nondet, histogram, activity, config, beta, copy_borders, sparse_loop=sparse)
        else:
            if alt_rule is None:
                sim_obj = cagen.ElementarySimulator(size, nondet, histogram, activity, rule, config, beta, copy_borders, base=base, sparse_loop=sparse)
            else:
                alt_rule = None if alt_rule == -1 else alt_rule
                compu = cagen.DualRuleCellularAutomaton(rule, alt_rule, nondet)
                sf_obj = cagen.automatic_stepfunc(size=size, config=config,
                        computation=compu, histogram=histogram, activity=activity,
                        copy_borders=copy_borders, base=base,
                        needs_random_generator=True, sparse_loop=sparse)
                sf_obj.gen_code()
                print compu.pretty_print()
                print compu.rule_a, compu.rule_b
                sim_obj = CagenSimulator(sf_obj, sf_obj.target)

    if "rule" in sim_obj.target_attrs:
        print sim_obj.pretty_print()
        print sim_obj.t.rule, hex(sim_obj.rule_number)

    display = ZasimDisplay(sim_obj)
    display.set_scale(scale)

    display.control.start()

    if black is not None:
        display.control.zero_percentage.setValue(black)

    if histogram:
        extra_hist = HistogramExtraDisplay(sim_obj, parent=display, height=200, maximum= w * h)
        extra_hist.show()
        display.window.attach_display(extra_hist)

    if activity:
        extra_activity = HistogramExtraDisplay(sim_obj, attribute="activity", parent=display, height=200, maximum=w*h)
        extra_activity.show()
        display.window.attach_display(extra_activity)
        display.window.addDockWidget(Qt.RightDockWidgetArea, extra_activity)

