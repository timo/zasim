"""A Simulator object holds together information about and functionality of
cellular automaton simulators."""

try:
    from PySide.QtCore import QObject, Signal
except ImportError:
    try:
        from PyQt4.QtCore import pyqtSignal as QObject, Signal
    except ImportError:
        from zasim.lightweight_signal import Signal
        QObject = object

class BaseSimulator(QObject):
    """This class serves as the base for simulator objects."""

    shape = ()
    """The shape of the cellular space of this automaton.

    It's a tuple with the size of each dimension as entries.

    .. note ::
        This excludes any borders that have redundant cells in them."""

    step_number = 0
    """The number of the current step, beginning with the initial configuration
    being step 0."""

    available_history = 0
    """How many steps back the simulator can go."""

    prepared = True
    """Wether the simulator needs to run any kind of preparation before being
    able to perform steps"""

    rect_updated = Signal(tuple)
    """Is emitted when only a rectangular shaped area of the conf has changed."""

    positions_updated = Signal(list)
    """Is emitted when only a list of cells have changed."""

    updated = Signal()
    """Is emitted when the shape of changed cells is unknown or not
    interesting."""

    started = Signal()
    """Is emitted when continuous updating has been started."""

    stopped = Signal()
    """Is emitted when continuous updating has been stopped."""

    shapshot_taken = Signal()
    """Is emitted when a snapshot has been taken."""

    snapshot_restored = Signal()
    """Is emitted when a snapshot is restored."""

    def getConf(self):
        """Returns the configuration space as a numpy array. Its shape matches
        up with :attr:`shape`, so it also does not include any borders."""

    def step(self):
        """Step the simulator once."""
        self.updated.emit()

    def copy(self):
        """Duplicate the simulator."""

    def start(self):
        """Call this to notify views, that continuous updates have
        been started."""

    def stop(self):
        """Call this to notify views, that continuous updates have
        been stopped."""

    def snapshot(self):
        """Get a lightweight snapshot of this simulator, that can be restored
        again later on.

        .. note ::
            This emits the :attr:`snapshot_taken` signal."""

    def restore(self, snapshot):
        """Restore the simulator to an earlier state.

        .. note ::
            This emits the :attr:`sanpshot_restored` signal."""
