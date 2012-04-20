from zasim.external.qt import (
        QDialog, QSlider, QPushButton, QSpinBox, QVBoxLayout, QHBoxLayout,
        QTimer, Qt, app)
from zasim.gui.displaywidgets import DisplayWidget

from zasim.cagen.dualrule import DualRuleCellularAutomaton
from zasim.cagen.simulators import automatic_stepfunc
from zasim.simulator import CagenSimulator
from zasim.config import RandomInitialConfiguration

class DualRuleGadget(QDialog):
    def __init__(self):
        super(DualRuleGadget, self).__init__()

        self.rule_a = 184
        self.rule_b = 232
        self.probability = 0.99

        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self.stepsim)

        self.conf = RandomInitialConfiguration(2, 0.5, 0.5).generate((300,))
        self.create_stepfunc()
        self.init_gui()
        self.make_connections()
        self.sim_timer.start(0)

    def create_stepfunc(self):
        compu = DualRuleCellularAutomaton(self.rule_a, self.rule_b, self.probability)
        sf_obj = automatic_stepfunc(config=self.conf,
                computation=compu, activity=True,
                copy_borders=True, base=2, sparse_loop=True,
                needs_random_generator=True)
        sf_obj.gen_code()
        self.sim = CagenSimulator(sf_obj)

    def init_gui(self):
        # a box to hold the UI elements at the top
        self.control_box = QHBoxLayout()

        # edit boxes for the rule numbers
        self.rule_a_edit = QSpinBox(self)
        self.rule_b_edit = QSpinBox(self)

        for box in (self.rule_a_edit, self.rule_b_edit):
            box.setRange(0, 255)

        self.rule_a_edit.setValue(self.rule_a)
        self.rule_b_edit.setValue(self.rule_b)

        # this slider lets you assign probabilities
        self.probab_slider = QSlider(Qt.Horizontal, self)
        self.probab_slider.setRange(0, 1000)
        self.probab_slider.setSingleStep(10)
        self.probab_slider.setValue(self.probability * 100)

        # with this button you build a new config
        self.reroll_conf = QPushButton("Re-roll config", self)

        self.control_box.addWidget(self.rule_a_edit)
        self.control_box.addWidget(self.probab_slider)
        self.control_box.addWidget(self.rule_b_edit)
        self.control_box.addWidget(self.reroll_conf)

        self.whole_layout = QVBoxLayout()
        self.whole_layout.addLayout(self.control_box)

        # this widget displays the configuration
        self.displaywidget = DisplayWidget(self.sim)
        self.displaywidget.set_scale(2)
        self.whole_layout.addWidget(self.displaywidget)

        self.setLayout(self.whole_layout)

    def make_connections(self):
        # when the displaywidget is fully rendered, stop the timer
        self.displaywidget.display.image_wrapped.connect(self.sim_timer.stop)

        # when any change is made, change everything
        self.probab_slider.sliderMoved.connect(self.slot_change_settings)
        self.probab_slider.valueChanged.connect(self.slot_change_settings)
        self.rule_a_edit.valueChanged.connect(self.slot_change_settings)
        self.rule_b_edit.valueChanged.connect(self.slot_change_settings)

        # the reroll conf button calls slot_reroll_conf
        self.reroll_conf.clicked.connect(self.slot_reroll_conf)

    def slot_line_wrapped(self):
        self.image_finished = True

    def slot_change_settings(self):
        print "changes"
        self.rule_a = self.rule_a_edit.value()
        self.rule_b = self.rule_b_edit.value()
        self.probability = self.probab_slider.value() / 100.

        self.displaywidget.display.image_wrapped.disconnect(self.sim_timer.stop)
        self.create_stepfunc()
        self.displaywidget.switch_simulator(self.sim)
        self.displaywidget.set_scale(2)
        self.displaywidget.display.image_wrapped.connect(self.sim_timer.stop)

        self.sim_timer.start(0)

    def slot_reroll_conf(self):
        self.conf = RandomInitialConfiguration(2, 0.5, 0.5).generate(self.sim.shape)
        self.slot_change_settings()

    def stepsim(self):
        self.sim.step()

if __name__ == "__main__":
    import sys

    gadget = DualRuleGadget()
    gadget.show()

    sys.exit(app.exec_())
