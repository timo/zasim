"""A Simulator object holds together information about and functionality of
cellular automaton simulators.


"""
# This file is part of zasim. zasim is licensed under the BSD 3-clause license.
# See LICENSE.txt for details.


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

class SimulatorInterface(QObject):
    """This class serves as the base for simulator objects.

    .. note::
        If you ever derive from this class and you get an error like
        "PySide.QtCore.Signal object has no attribute 'emit'", then you
        have most likely forgotten to call super's __init__."""

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

    palette_info = {}
    """Dictionary fro different display options and their extra data.

    colors32: list or dictionary of 32bit padded RGB values, like QImage::Format_RGB32
    qcolors:  list or dictionary of QColor values
    tiles:    dictionary with 'images', an image map and 'rects', a dictionary of rects
    chars:    list or dictionary of ascii/unicode values
    cboxes:   list or dictionary of multiline ascii/unicode values
    hexcols:  list or dictionary of colors usable in css-like color definitions.
    """

    #rect_updated = Signal(tuple)
    #"""Is emitted when only a rectangular shaped area of the conf has changed."""

    updated = Signal()
    """Is emitted when the conf has changed as result of a step."""

    changed = Signal()
    """Is emitted when the configuration has changed, but there was no step."""

    started = Signal()
    """Is emitted when continuous updating has been started."""

    stopped = Signal()
    """Is emitted when continuous updating has been stopped."""

    shapshot_taken = Signal()
    """Is emitted when a snapshot has been taken."""

    snapshot_restored = Signal()
    """Is emitted when a snapshot is restored or a completely new configuration
    has been set."""

    target_attrs = []
    """The extra-attributes the target has to offer, such as histogram."""

    t = TargetProxy(object(), [])
    """A proxy object to access the target_attrs."""

    changeinfo = None
    """Information about the last configuration change.

    May be
    1. a rectangle (x, y, w, h) that has been changed
    2. None, if everything changed."""

    def get_config(self):
        """Returns a copy of the configuration space as a numpy array.
        Its shape matches up with :attr:`shape`, so it also does not
        include any borders."""

    def set_config(self, config):
        """Sets a new config for the simulator.

        Emits snapshot_restored"""

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

    def reset(self, configurator=None):
        """Reset the simulator by using the same generator that was initially
        used, if it's still available, or set a new configurator for the future
        and reset the configuration with it once.

        See also `cagen.config`"""
        raise NotImplementedError("reset not implemented.")

class CagenSimulator(SimulatorInterface):
    """This Simulator takes a `StepFunc` instance and packs it in an interface
    compatible with `SimulatorInterface`."""

    def __init__(self, step_func):
        super(CagenSimulator, self).__init__()
        self._step_func = step_func
        self._target = step_func.target
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
        self.snapshot_restored.emit()

    def set_config_value(self, pos, value=None):
        try:
            self._step_func.set_config_value(pos, value)
        except IndexError:
            return
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

    def reset(self, configurator=None):
        if configurator is not None:
            self._target._reset_generator = configurator
        if self._target._reset_generator:
            newconf = self._target._reset_generator.generate(size_hint=self._target._reset_size)
            self.set_config(newconf)
        else:
            raise ValueError("This simulator's target wasn't created with a generator as config value.")

    def __str__(self):
        try:
            return str(self._step_func)
        except:
            return repr(self)

class ElementaryCagenSimulator(CagenSimulator):
    """This Simulator has a few special options available only if you have an
    elementary step func with a rule number."""

    rule_number = 0
    """The rule number of the target."""

    def __init__(self, step_func, rule_nr):
        super(ElementaryCagenSimulator, self).__init__(step_func=step_func)
        self.rule_number = rule_nr
