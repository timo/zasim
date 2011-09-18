from ..external.qt import *
from .stepfunc import StepFuncCompositionDialog
from .elementary import ElementaryRuleWindow

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
        layout.addWidget(sim_name)

        scroller = QScrollArea()
        scroller.setWidget(self.display)

        layout.addWidget(scroller)
        layout.addWidget(self.control)
        self.control.setObjectName("control")

        self.setCentralWidget(central_widget)

        self.control.start_inverting_frames.connect(self.display.start_inverting_frames)
        self.control.stop_inverting_frames.connect(self.display.stop_inverting_frames)

        self.setup_menu()

        self.elementary_tool = None
        self.comp_dlg = None

    def setup_menu(self):
        simulator_menu = self.menuBar().addMenu("Simulator")
        simulator_menu.setObjectName("simulator_menu")
        new_a = simulator_menu.addAction("&New...")
        new_a.setObjectName("new")
        new_a.activated.connect(self.show_new_sim_dlg)
        stepf_a = simulator_menu.addAction("Open &Stepfunc Table")
        stepf_a.setObjectName("stepfunc_table")
        stepf_a.activated.connect(self.open_elementary_tool)
        quit_a = simulator_menu.addAction("&Quit")
        quit_a.setObjectName("quit")
        quit_a.activated.connect(self.close)

    def open_elementary_tool(self):
        if self.elementary_tool and not self.elementary_tool.isVisible():
            self.elementary_tool = None
        if self.elementary_tool is None:
            self.elementary_tool = ElementaryRuleWindow(self.simulator._step_func.neigh, self.simulator.rule_number, base=len(self.simulator.t.possible_values))
            self.elementary_tool.setObjectName("elementary_tool")
            self.elementary_tool.show()

    def show_new_sim_dlg(self):
        try:
            if self.comp_dlg and not self.comp_dlg.isVisible():
                self.comp_dlg = None
        except RuntimeError: # the object on the C++ side had already been deleted
            self.comp_dlg = None
        if self.comp_dlg is None:
            self.comp_dlg = StepFuncCompositionDialog()
            self.comp_dlg.setObjectName("composition_dialog")
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
