from ..external.qt import *
from .elementary import CellDisplayWidget
from ..display.qt import make_palette_qc

from ..config import BaseRandomConfiguration

class_to_resetter = {}
def reg_resetter(base_class):
    def register_func(cls):
        class_to_resetter[base_class] = cls
        return cls
    return register_func

class BaseResetter(QWidget):
    def __init__(self, mainwin, **kwargs):
        super(BaseResetter, self).__init__(**kwargs)

        self._mw = mainwin
        self._sim = self._mw.simulator

        self.values = self._sim.t.possible_values

        try:
            if self._sim._target._reset_generator is not None:
                self.take_over_settings(self._sim._target._reset_generator)
        except:
            pass

        self.setup_ui()
        self.set_values()

    def setup_ui(self):
        """This method sets up the widgets that the user can manipulate to
        generate different kinds of configurations."""

    def set_values(self):
        """This method changes the widgets to represent the internal state
        of the Resetter."""

    def take_over_settings(self, configuration=None):
        """Either take over the settings of another configurator or reset
        the settings to the last used configurator."""

    def generate_generator(self):
        """Generate a matching configuration generator from the settings."""

@reg_resetter(BaseRandomConfiguration)
class BaseRandomConfigurationResetter(BaseResetter):
    perc_widgets = {}

    friendly_name = "Random Configuration"

    setting_values = False

    def take_over_settings(self, configuration=None):
        print "taking over settings!"
        if configuration:
            self.original_configuration = configuration
        else:
            configuration = self.original_configuration

        self.values = configuration.values
        self.percs = list(configuration.percentages)

    def setup_ui(self):
        whole_layout = QVBoxLayout()
        print self.percs
        for index, value in enumerate(self.values):
            side_by_side = QHBoxLayout()
            if "colors_qc" not in self._sim.palette_info:
                self._sim.palette_info["colors_qc"] = make_palette_qc(self._sim.palette_info["colors32"])
            palette_repr = CellDisplayWidget(value=value, palette=self._sim.palette_info["colors_qc"], parent=self)
            side_by_side.addWidget(palette_repr)

            perc_widget = QDoubleSpinBox(self)
            perc_widget.setMaximum(1)
            perc_widget.setMinimum(0)
            perc_widget.setValue(self.percs[value])
            perc_widget.setSingleStep(0.01)
            perc_widget.setDecimals(4)
            def value_changed_with_index(new_value, index=index):
                self.perc_changed(new_value, index)
            perc_widget.valueChanged.connect(value_changed_with_index)
            self.perc_widgets[index] = perc_widget
            side_by_side.addWidget(perc_widget)

            whole_layout.addLayout(side_by_side)

        self.setLayout(whole_layout)

    def set_values(self):
        self.setting_values = True
        try:
            for value in self.values:
                perc_widget = self.perc_widgets[value]
                perc_widget.setValue(self.percs[value])
        finally:
            self.setting_values = False

    def perc_changed(self, new_value, index):
        if self.setting_values:
            return
        old_value = self.percs[index]
        change = new_value - old_value

        self.percs[index] = new_value

        others = len(self.percs) - 1

        print index, new_value, self.perc_widgets

        for i in self.perc_widgets.keys():
            if i == index:
                continue
            print i
            self.percs[i] -= change / float(others)

        almost_all = sum(self.percs[:-1])
        self.percs[-1] = 1.0 - almost_all

        self.set_values()

class ResetDocklet(QDockWidget):
    """This dockwidget lets the user choose from a wide variety of
    config generators."""

    resetters = {}

    current_resetter = None

    def __init__(self, mainwin, **kwargs):
        super(ResetDocklet, self).__init__(**kwargs)
        self.setAllowedAreas(Qt.RightDockWidgetArea)
        self.setFloating(False)

        self._mw = mainwin

        self.setup_ui()
        self.switch_resetter(0)

    def setup_ui(self):
        centralwidget = QWidget()

        whole_layout = QVBoxLayout()

        resetter_selecter = QComboBox(self)
        for cls in class_to_resetter.values():
            resetter_selecter.addItem(cls.friendly_name, cls)
        resetter_selecter.currentIndexChanged.connect(self.switch_resetter)

        whole_layout.addWidget(resetter_selecter)
        self.resetter_selecter = resetter_selecter

        self.resetters_layout = QVBoxLayout()
        self.dummy_widget = QWidget()
        self.dummy_widget.hide()
        self.resetters_layout.addWidget(self.dummy_widget)
        whole_layout.addLayout(self.resetters_layout)

        dismiss_button = QPushButton("reset changes")
        dismiss_button.clicked.connect(self.dismiss_changes)
        whole_layout.addWidget(dismiss_button)

        reset_button = QPushButton("Generate new")
        whole_layout.addWidget(reset_button)

        self.whole_layout = whole_layout
        centralwidget.setLayout(self.whole_layout)

        self.setWidget(centralwidget)

    def switch_resetter(self, index):
        cls = self.resetter_selecter.itemData(index)
        if cls in self.resetters:
            print "taking already existing resetter"
            current_resetter.hide()
            w = self.resetters[cls]
            w.show()
        else:
            print "making new resetter"
            w = cls(self._mw, parent=self)
            self.resetters[cls] = w
            self.resetters_layout.addWidget(w)
            w.show()
            self.whole_layout.update()

        self.current_resetter = w

    def dismiss_changes(self):
        self.current_resetter.take_over_settings()
        self.current_resetter.set_values()

