from ..external.qt import *
from .elementary import CellDisplayWidget

from ..config import BaseRandomConfiguration

class_to_resetter = {}
def reg_resetter(base_class):
    def register_func(cls):
        class_to_resetter[base_class] = cls
        return cls

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

@reg_resetter(BaseRandomConfiguration)
class BaseRandomConfigurationResetter(BaseResetter):
    perc_widgets = {}

    friendly_name = "Random Configuration"

    def take_over_settings(self, configuration=None):
        if configuration:
            self.original_configuration = configuration
        else:
            configuration = self.original_configuration

        self.values = configuration.values
        self.percs = configuration.percentages

    def setup_up(self):
        whole_layout = QHBoxLayout()
        for value in self.values:
            side_by_side = QVBoxLayout()
            palette_repr = CellDisplayWidget(value=value, palette=self._sim.palette_info["colors_qc"], parent=self)
            side_by_side.addWidget(palette_repr)

            perc_widget = QDoubleSpinBox(self)
            perc_widget.setMaximum(1)
            perc_widget.setMinimum(0)
            perc_widget.setValue(self.percs[value])
            perc_widget.setSingleStep(0.01)
            perc_widget.setDecimals(4)
            self.perc_widgets.append(perc_widget)
            side_by_side.addWidget(perc_widget)

            whole_layout.addLayout(side_by_side)

        self.setLayout(whole_layout)

    def set_values(self):
        for value in self.values:
            perc_widget = self.perc_widgets[value]
            perc_widget.setValue(self.percs[value])


class ResetDocklet(QDockWidget):
    """This dockwidget lets the user choose from a wide variety of
    config generators."""

    def __init__(self, sim, **kwargs):
        self.setAllowedAreas(Qt.RightDowkWidgetArea)
        self.setFloating(False)

    def setup_up(self):
        whole_layout = QHBoxLayout()

        resetter_selecter = QComboBox(self)
        for cls in class_to_resetter.values():
            resetter_selecter.addItem(cls.friendly_name, cls)

        whole_layout.addWidget(resetter_selecter)
        self.resetter_selecter = resetter_selecter

        self.setLayout(whole_layout)
