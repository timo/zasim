"""A Simulator object holds together information about and functionality of
cellular automaton simulators."""

try:
    from .external.qt import QObject, Signal
except ImportError:
    from zasim.lightweight_signal import Signal
    QObject = object
    print "using lightweight signal"

class TargetProxy(object):
    def __init__(self, target, attrs):
        self.target = target
        self.attrs = attrs

    def __getattr__(self, attr):
        if attr in self.attrs:
            return getattr(self.target, attr)
        else:
            raise AttributeError("%s not in target attrs" % attr)

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

    #rect_updated = Signal(tuple)
    #"""Is emitted when only a rectangular shaped area of the conf has changed."""

    #positions_updated = Signal(list)
    #"""Is emitted when only a list of cells have changed."""

    updated = Signal()
    """Is emitted when the shape of changed cells is unknown or not
    interesting."""

    changed = Signal()
    """Is emitted when the configuration has changed, but there was no step."""

    started = Signal()
    """Is emitted when continuous updating has been started."""

    stopped = Signal()
    """Is emitted when continuous updating has been stopped."""

    shapshot_taken = Signal()
    """Is emitted when a snapshot has been taken."""

    snapshot_restored = Signal()
    """Is emitted when a snapshot is restored."""

    target_attrs = []
    """The extra-attributes the target has to offer, such as histogram."""

    t = TargetProxy(object(), [])
    """A proxy object to access the target_attrs."""

    def get_config(self):
        """Returns a copy of the configuration space as a numpy array.
        Its shape matches up with :attr:`shape`, so it also does not
        include any borders."""

    def set_config(self, config):
        """Sets a new config for the simulator."""

    def set_config_value(self, pos, value=None):
        """Set the config value at pos to value.

        If value is None, flip the value instead."""

    def step(self):
        """Step the simulator once."""
        self.updated.emit()
        self.step_number += 1

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
    """This Simulator takes a `StepFunc` and a `TestTarget`
    instance and packs them together so they are compatible with the
    `BaseSimulator` interface."""

    def __init__(self, step_func, target):
        super(CagenSimulator, self).__init__()
        self._step_func = step_func
        self._target = target
        self._size = self._target.size
        self._bbox = self._step_func.neigh.bounding_box()
        self.shape = self._size

        self.prepared = self._step_func.prepared

        self.t = TargetProxy(self._target, self._step_func.attrs + ["possible_values"])

    def get_config(self):
        """Return the config, sans borders."""
        if len(self.shape) == 1:
            ((l, r),) = self._bbox
            return self._target.cconf[abs(l):-abs(r)].copy()
        elif len(self.shape) == 2:
            (l, r), (u, d) = self._bbox
            return self._target.cconf[abs(u):-abs(d),abs(l):-abs(r)].copy()

    def set_config(self, config):
        self._step_func.set_config(config)
        self.updated.emit()

    def set_config_value(self, pos, value=None):
        self._step_func.set_config_value(pos[::-1], value)
        self.changed.emit()

    def step(self):
        """Delegate the stepping to the :meth:`StepFunc.step` method, then
        emit :attr:`updated`."""
        self._step_func.step()
        # XXX what's the order? what happens if a slot called from here changes something?
        self.prepared = True
        self.step_number += 1
        self.updated.emit()

    def step_inline(self):
        """Step the simulator using the weave.inline version of the code."""
        self._step_func.step_inline()
        self.prepared = True
        self.step_number += 1
        self.updated.emit()

    def step_pure_py(self):
        """Step the simulator using the pure python code version."""
        self._step_func.step_pure_py()
        self.step_number += 1
        self.updated.emit()

    def __str__(self):
        return str(self._step_func)

class ElementaryCagenSimulator(CagenSimulator):
    """This Simulator has a few special options available only if you have an
    elementary step func with a rule number."""

    rule_number = 0
    """The rule number of the target."""

    def __init__(self, step_func, target, rule_nr):
        super(ElementaryCagenSimulator, self).__init__(step_func=step_func, target=target)
        self.rule_number = rule_nr
