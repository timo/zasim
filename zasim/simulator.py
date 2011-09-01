"""A Simulator object holds together information about and functionality of
cellular automaton simulators."""

try:
    from PySide.QtCore import QObject, Signal
except ImportError:
    try:
        from PyQt4.QtCore import pyqtSignal as Signal
        from PyQt4.QtCore import QObject
        print "using PyQt4 signal"
    except ImportError:
        from zasim.lightweight_signal import Signal
        QObject = object
        print "using lightweight signal"

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
        """Returns a copy of the configuration space as a numpy array.
        Its shape matches up with :attr:`shape`, so it also does not
        include any borders."""

    def step(self):
        """Step the simulator once."""
        self.updated.emit()

    def copy(self):
        """Duplicate the simulator."""

    def start(self):
        """Call this to notify views, that continuous updates have
        been started."""
        self.started.emit()

    def stop(self):
        """Call this to notify views, that continuous updates have
        been stopped."""
        self.stopped.emit()

    def snapshot(self):
        """Get a lightweight snapshot of this simulator, that can be restored
        again later on.

        .. note ::
            This emits the :attr:`snapshot_taken` signal."""
        self.snapshot_taken.emit()

    def restore(self, snapshot):
        """Restore the simulator to an earlier state.

        .. note ::
            This emits the :attr:`sanpshot_restored` signal."""
        raise NotImplementedError("restoring of snapshots not implemented"\
                                  "for %s" % (self.__class__))

class CagenSimulator(BaseSimulator):
    """This Simulator takes a :class:`WeaveStepFunc` and a :class:`TestTarget`
    instance and packs them together so they are compatible with the
    :class:`BaseSimulator` interface."""
    def __init__(self, step_func, target):
        super(CagenSimulator, self).__init__()
        self._step_func = step_func
        self._target = target
        self._size = self._target.size
        self._bbox = self._step_func.neigh.bounding_box()
        self.shape = self._size

        self.prepared = self._step_func.prepared

    def getConf(self):
        """Return the config, sans borders."""
        if len(self.shape) == 1:
            ((l, r),) = self._bbox
            return self._target.cconf[abs(l):-abs(r)].copy()
        elif len(self.shape) == 2:
            (l, r), (u, d) = self._bbox
            return self._target.cconf[abs(u):-abs(d),abs(l):-abs(r)].copy()

    def step(self):
        """Delegate the stepping to the :meth:`WeaveStepFunc.step` method, then
        emit :attr:`updated`."""
        self._step_func.step()
        self.prepared = True
        self.updated.emit()