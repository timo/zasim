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

.. seealso::

    The program developed in this section can be run from an installed
    zasim or a source checkout by calling::

        python -m zasim.examples.dualrule.main

    The code can be found in `zasim/examples/dualrule/`

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
        self.probab_slider.setValue(1000 - self.probability * 1000)

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

Running the simulation
----------------------

Our simulator should run as fast as possible until the display area has
been filled. For that, the `~display.qt.OneDimQImagePainter` offers the
signal `image_wrapped`. Each step of the simulator can be started by a
QTimer that's set to run as fast as possible by starting it with a `delay`
of 0.

Instant feedback
----------------

Whenever something has changed, we need to reset the simulator. The only
way to do this 100% properly is to create a new simulator every time a
change was made. The following function will create a simulator for us::

    def create_stepfunc(self):
        compu = DualRuleCellularAutomaton(self.rule_a, self.rule_b, self.probability)
        sf_obj = automatic_stepfunc(config=self.conf,
                computation=compu, activity=True,
                copy_borders=True, base=2, sparse_loop=True,
                needs_random_generator=True)
        sf_obj.gen_code()
        self.sim = CagenSimulator(sf_obj)

It will use the config `self.conf`, which will be generated once at the
start and then every time the reroll config button is pushed.

Additionally, we need a function to react to all changes::

    def slot_change_settings(self):
        self.rule_a = self.rule_a_edit.value()
        self.rule_b = self.rule_b_edit.value()
        self.probability = 1.0 - (self.probab_slider.value() / 1000.)

        # if we don't disconnect the signal, the old displays might be kept
        # instead of deleted by the garbage collector.
        self.displaywidget.display.image_wrapped.disconnect(self.sim_timer.stop)
        self.create_stepfunc()
        self.displaywidget.switch_simulator(self.sim)
        self.displaywidget.set_scale(2)
        self.displaywidget.display.image_wrapped.connect(self.sim_timer.stop)

        # since we have changed things, run the simulation as fast as possible.
        self.sim_timer.start(0)

    def slot_reroll_conf(self):
        self.conf = RandomConfiguration(2, 0.5, 0.5).generate(self.sim.shape)
        self.slot_change_settings()

These slots will be connected to our user interface::

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

Finally, at the very beginning of the class, we initialise all our things::

    def __init__(self):
        super(DualRuleGadget, self).__init__()

        self.rule_a = 184
        self.rule_b = 232
        self.probability = 0.99

        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self.stepsim)

        # here the size of our configuration is chosen.
        self.conf = RandomConfiguration(2, 0.5, 0.5).generate((300,))
        self.create_stepfunc()
        self.init_gui()
        self.make_connections()
        self.sim_timer.start(0)

The `stepsim` method simply calls self.sim.step(). We need this because
we reassign self.sim all the time and we don't want to disconnect and
reconnect the timer over and over again.

General approach
----------------

In general, using zasim in your own GUI application is not terribly
complicated. Most classes in `zasim.gui` are widgets that you can just put
into your application and immediately use. Qt's signals and slots make it
fairly simple to connect elements together to do interesting things.
