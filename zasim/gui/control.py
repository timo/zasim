from ..external.qt import *
import numpy as np
from itertools import product
import random

class ControlWidget(QWidget):
    """Control a simulator with buttons or from the interactive console."""

    start_inverting_frames = Signal()
    stop_inverting_frames = Signal()

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
        self.start_button = QPushButton("&Start", self)
        self.start_button.setObjectName("start")
        self.stop_button = QPushButton("&Stop", self)
        self.stop_button.setObjectName("stop")
        self.stop_button.hide()

        delay = QSpinBox()
        delay.setMinimum(0)
        delay.setMaximum(10000)
        delay.setSuffix(" ms")
        delay.setValue(self.timer_delay)
        delay.setObjectName("delay")

        l.addWidget(self.start_button)
        l.addWidget(self.stop_button)
        l.addWidget(delay)

        l.addSpacing(11)
        reset_button = QPushButton("&reset", self)
        reset_button.clicked.connect(self.set_config)
        reset_button.setObjectName("reset")
        l.addWidget(reset_button)

        self.zero_percentage = QDoubleSpinBox(self)
        self.zero_percentage.setMaximum(1)
        self.zero_percentage.setMinimum(0)
        self.zero_percentage.setValue(0.5)
        self.zero_percentage.setSingleStep(0.01)
        self.zero_percentage.setDecimals(4)
        self.zero_percentage.setSuffix(" black")
        self.zero_percentage.setObjectName("zero_percentage")
        l.addWidget(self.zero_percentage)

        self.invert_frames = QCheckBox(self)
        self.invert_frames.setChecked(False)
        self.invert_frames.setText("&invert odd frames")
        self.invert_frames.stateChanged.connect(self.invert_odd)
        self.invert_frames.setObjectName("invert_frames")
        l.addWidget(self.invert_frames)

        self.framerate = FramerateWidget(self.sim)
        l.addWidget(self.framerate)

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
            conf = np.zeros(self.sim.get_config().shape, self.sim.get_config().dtype)
            positions = product(*[range(size) for size in conf.shape])
            zero_perc = self.zero_percentage.value()
            for pos in positions:
                if random.random() > zero_perc:
                    conf[pos] = random.choice(self.sim.t.possible_values[1:])

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
