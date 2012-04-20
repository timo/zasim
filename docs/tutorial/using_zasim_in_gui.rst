.. _tutorial_zasim_in_gui:

Using zasim in GUI
==================

Zasim offers a bunch of gui components, as can be seen in its own built-in
gui, but that's not all you can do with it; Most of the functionality is
spread across the components, which are all reusable and mostly decoupled.

In this tutorial we will be developing a tool to play around with `Dual
Rule CA <zasim.cagen.dualrule>`. A dual-rule CA is a nondeterministic
cellular automaton which has two different rules (like an elementary
cellular automaton would) and a probability to decide which rule to apply
to each cell.

The GUI that will be developed has two entry boxes for the rules and a
slider for the probability. There is a display for displaying the cellular
automaton and a button to change the starting configuration.

Mocking up the GUI
------------------

Using PyQt4 or PySide, creating the panel at the top for the sliders and
input boxes is rather simple. Explaining it in detail is beyond the scope
of this documentation, though. This is the code for creating the user interface::

    def init_gui(self):
        # a box to hold the UI elements at the top
        self.control_box = QHBoxLayout()

        # edit boxes for the rule numbers
        self.rule_a_edit = QSpinBox(self)
        self.rule_b_edit = QSpinBox(self)

        self.rule_a_edit.setRange(0, 255)
        self.rule_b_edit.setRange(0, 255)

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


