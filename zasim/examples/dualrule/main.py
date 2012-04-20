from zasim.external.qt import QDialog, QSlider, QPushButton, QSpinBox, QDoubleSpinBox, QVBoxLayout, QHBoxLayout
from zasim.gui.displaywidgets import DisplayWidget

class DualRuleGadget(QDialog):
    def __init__(self):
        self.init_gui()

    def init_gui(self):
        self.control_box = QVBoxLayout()

        self.rule_a_edit = QSpinBox(self)
        self.rule_b_edit = QSpinBox(self)

        for box in (self.rule_a_edit, self.rule_b_edit):
            box.setRange(0, 255)

        self.probab_slider = QSlider(self)
        self.probab_slider.setRange(0, 1000)
        self.probab_slider.setSingleStep(10)

        self.control_box.addWidget(self.rule_a_edit)
        self.control_box.addWidget(self.probab_slider)
        self.control_box.addWidget(self.rule_b_edit)

        self.reroll_conf = QPushButton("Re-roll config", self)

        self.whole_layout = QHBoxLayout()
        self.whole_layout.addLayout(self.control_box)

        self.displaywidget = DisplayWidget(None)

