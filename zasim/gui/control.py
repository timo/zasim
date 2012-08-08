from ..external.qt import *
import numpy as np
from itertools import product
import random

class ControlWidget(QWidget):
    """Control a simulator with buttons or from the interactive console."""

    def __init__(self, simulator, **kwargs):
        """:param simulator: The simulator object to control."""
        super(ControlWidget, self).__init__(**kwargs)

        self.sim = simulator

        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self.sim.step)

        self.timer_delay = 0

        self._setup_ui()

    def closeEvent(self, event):
        self.sim_timer.stop()

    def _setup_ui(self):
        """Setup the widgets, connect the signals&slots."""
        l = QHBoxLayout(self)

        self.step_button = QPushButton("Ste&p", self)
        self.step_button.setObjectName("step")
        self.start_button = QPushButton("&Run", self)
        self.start_button.setObjectName("start")
        self.stop_button = QPushButton("St&op", self)
        self.stop_button.setObjectName("stop")
        self.stop_button.hide()

        delay = QSpinBox()
        delay.setMinimum(0)
        delay.setMaximum(10000)
        delay.setSuffix(" ms")
        delay.setValue(self.timer_delay)
        delay.setObjectName("delay")

        l.addWidget(self.step_button)
        l.addWidget(self.start_button)
        l.addWidget(self.stop_button)
        l.addWidget(delay)

        self.framerate = FramerateWidget(self.sim)
        l.addWidget(self.framerate)

        self.setLayout(l)

        self.step_button.clicked.connect(self.sim.step)
        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        delay.valueChanged.connect(self.change_delay)

    def start(self):
        """Start running the simulator."""
        self.sim_timer.start(self.timer_delay)
        self.sim.start()
        self.start_button.hide()
        self.stop_button.show()

    def stop(self):
        """Stop the simulator."""
        self.sim_timer.stop()
        self.sim.stop()
        self.stop_button.hide()
        self.start_button.show()

    def change_delay(self, delay):
        """Change the timer delay of the simulator steps."""
        if isinstance(delay, basestring) and delay.endswith("ms"):
            delay = delay[:-2]
        self.timer_delay = int(delay)
        if self.sim_timer.isActive():
            self.start()

    def set_config(self, conf=None):
        if conf is None:
            try:
                self.sim.reset()
            except ValueError:
                print "simulator %s doesn't have a generator set."
        else:
            self.sim.set_config(conf)

class FramerateWidget(QLabel):
    def __init__(self, sim, **kwargs):
        super(FramerateWidget, self).__init__(**kwargs)

        self._sim = sim
        self._last_frame = sim.step_number

        self._sim.started.connect(self.started)
        self._sim.stopped.connect(self.stopped)

        self.setText("0 fps")

    def started(self):
        self.frame_timer = self.startTimer(1000)
        self._last_frame = self._sim.step_number

    def stopped(self):
        self.killTimer(self.frame_timer)
        self.setText("n/a fps")

    def timerEvent(self, event):
        frame = self._sim.step_number
        diff = frame - self._last_frame
        self._last_frame = frame

        self.setText("%d fps" % diff)
