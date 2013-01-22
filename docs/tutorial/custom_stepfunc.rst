.. _tutorial_stepfunc:

Assembling a custom StepFunc
============================

Until now, we just had to specify a few parameters and everything
fell into place for us. However, zasim offers a whole toolkit for
assembling `~zasim.cagen.stepfunc.StepFunc` objects from simpler parts
that all influence the behavior of the result. In this chapter, the
`StepFunc` object, the `~zasim.cagen.bases.StepFuncVisitor` objects and the
`~zasim.simulator.Simulator` interface will be explored. The next chapter will
be about replacing those `StepFuncVisitors` with our own creations and seeing
what happens.


Holding it all together: `~zasim.cagen.stepfunc.StepFunc`
---------------------------------------------------------

The job of the `StepFunc` object is to make sure the individual `StepFuncVisitor`
objects you decide to throw into the blender all play nice together or, if they
won't, report incompatibilities.

It has pre-set slots for a few different types of `StepFuncVisitor` objects,
each contributing a different kind of functionality, but with a somewhat fixed
interface. Those slots are:

 * A `~zasim.cagen.bases.CellLoop` instance (as the `loop` keyword
   argument) decides, what cells have to be considered for the step and in
   what order. Here are some examples of `CellLoop` classes that are already
   there:

   - `~zasim.cagen.loops.OneDimCellLoop` and `~zasim.cagen.loops.TwoDimCellLoop`
     loop over all cells in the configuration.

   - `~zasim.cagen.nondeterministic.OneDimNondeterministicCellLoop`
     and the `two-dimensional version
     <zasim.cagen.nondeterministic.TwoDimNondeterministicCellLoop>`
     have a parameter that defines with what probability each of the cells will
     be considered.

   Other possibilities include a loop that only considers cells for an update
   if there were changes in their neighbourhood in the last step.

 * A `~zasim.cagen.bases.StateAccessor` instance (as the `accessor` keyword
   argument) has all knowledge about how the state is kept and offers access to
   the data as well as meta-data. Beyond that, it creates code, that writes the
   result of the computation into the state data storage. These are two of the
   `StateAccessor` classes that can already be found in zasim:

   - `~zasim.cagen.accessors.SimpleStateAccessor` keeps the configuration in a
     numpy array with one or two dimensios.

   - `~zasim.cagen.beta_async.BetaAsynchronousAccessor` works almost the same
     as the `SimpleStateAccessor`, but takes care of correctly handling
     the internal and external state of each cell, as described in
     `the beta_async module <zasim.cagen.beta_async>`.

   Possible future ideas are storing the data in a sparse way and not limiting
   the size of the configuration.

 * A `~zasim.cagen.bases.Neighbourhood` instance (as the `neighbourhood` keyword
   argument), whose sole responsibility is to make the data from all neighbours
   available to the computational part of the step func later on. In its most
   basic form, the `~zasim.cagen.neighbourhoods.SimpleNeighbourhood`, it stores
   a list of names for the neighbourhood cells and their positional offsets and
   just reads them at the beginning of the loop.

 * A `~zasim.cagen.bases.BorderHandler` instance (as the `border` keyword
   argument), that does things like copying the borders from the sides and at
   the same time ensuring the size of the configuration storage is big enough
   to keep those extra cells. It could also do things like set the border cells
   to changing values or anything you could think of.

   They also offer functions `~zasim.cagen.bases.BorderHandler.is_position_valid`
   and `~zasim.cagen.bases.BorderHandler.correct_position` for other components
   to figure out if positions are valid and if they are invalid, what to do
   with them. The `~zasim.cagen.loops.SparseCellLoop` uses these functions to
   correctly mark neighbourhood cells as active if there was a change.

 * A `~zasim.cagen.bases.ExtraStats` instance (in the `visitors` list, as
   well), which gathers some additional statistics about the step function
   execution. The following two `ExtraStats` classes are already available:

   - `~zasim.cagen.stats.SimpleHistogram` counts, how many cells have each
     possible value.

   - `~zasim.cagen.stats.ActivityRecord` counts, how many cells have changed
     their value in one step.

 * Finally, a `~zasim.cagen.bases.Computation` instance (in the `visitors`
   list), that does the actual computation. Examples include:

   - `~zasim.cagen.computations.ElementaryCellularAutomatonBase`, a class, that
     implements elementary cellular automatons for any neighbourhood and number
     of dimensions

   - `~zasim.cagen.computations.CountBasedComputationBase`, a base class, that
     offers a local variable `nonzerocount` inside the loop, that holds the
     number of cells from the neighbourhood, that are not zero.

   - Based on the `CountBasedComputationBase`, the
     `~zasim.cagen.computations.LifeCellularAutomatonBase`, that implements
     Conways Game of Life.

   The other possibilities are almost limitless. CAs like the SandPile CA, the
   cellular automaton originally envisioned by Von Neumann, Langton's ant or
   any other would have the bulk of their implementation in one of those. Some
   may also need special instances of `CellLoop` or `StateAccessor` to work.

The `StepFunc` works by calling each of the following methods on all
`StepFuncVisitors`:

 * `~zasim.cagen.bases.StepFuncVisitor.bind` with itself as the `code` argument.
   This binds the StepFuncVisitor to the StepFunc. The StepFuncVisitor should
   not allow another StepFunc to bind it to itself after this.

 * `~zasim.cagen.bases.StepFuncVisitor.visit`, to let it generate any code for
   the step function body

 * `~zasim.cagen.bases.StepFuncVisitor.set_target` with the target instance as
   the `target` argument. This makes the target accessible to the
   StepFuncVisitor, so that any new attributes [1]_ can be set.

 * `~zasim.cagen.bases.StepFuncVisitor.init_once`, which allows for actions,
   that depend on the target, but are only needed to be run once, not whenever
   the configuration has changed.

 * `~zasim.cagen.bases.StepFuncVisitor.new_config`, in which the StepFuncVisitor
   can perform any tasks necessary to bring a changed configuration into a sane
   state. Any `BorderHandler`, for instance, would work their magic here.

.. [1] For an example of this, see 
       `zasim.cagen.nondeterministic.NondeterministicCellLoopMixin.set_target`,
       which populates the randseed attribute, that was previously added to the
       targets attribute list in the visit method.

There are other actions, that happen, which don't fit this pattern:

 * At the very beginning, the `StepFunc` will tell the `StateAccessor`, how
   big the configuration array is, by calling its `set_size` method.

 * After `new_config` has been called on all visitors, the `StepFunc` will call
   `~zasim.cagen.bases.StateAccessor.multiplicate_config`, which takes care of
   populating a kind of history of configs. Usually, a `StateAccessor` would
   keep at least a *current config* and a *next config* internally. This is the
   code, that makes sure, that every external change to the configuration will
   be reflected in both of these.

 * After setting the size on the accessor, it will extract the `possible_values`
   property of the target instance and set self.possible_values to it.

 * After calling `bind` on all visitors, the StepFunc will `run a compatibility
   check <zasim.cagen.stepfunc.StepFunc._check_compatibility>` of all
   StepFuncVisitors, to make sure simple errors like using a loop for one
   dimension with a configuration, that's two-dimensional, will get
   noticed straight away.

And `StepFunc` has another neat feature. Each visitor is able to contribute a
little part to a common name for the StepFunc. Such a name is generated when
calling str on the StepFunc and will call build_name on all StepFuncVisitor
objects that are part of the StepFunc. A name could be, for instance::

    2d with VonNeumannNeighbourhood (copy borders) calculating rule 0x915b8b0a (histogram)
    1d with ElementaryFlatNeighbourhood calculating rule 0xa5
    2d with MooreNeighbourhood calculating game of life (activity)

.. _tutorial_stepfunc_target:

Keeping the data together: the `Target`
---------------------------------------

In the previous section, the *target instance* has been mentioned, but there was
not yet any explanation for what it is or does. The target is, however, very
simple. All it has to do is basically keep the configuration and a bunch of
additional attributes together in one namespace. The only class currently useful
as a target is the `~zasim.cagen.target.Target`, which takes a config - or
a size, which will generate a random config - and a base as arguments and offers
the attributes `cconf` and `possible_values`.

Additional attributes will then be added by the `StepFunc` on an as-needed
basis. These include `nconf`, the "next configuration" set by the
`SimpleStateAccessor`, `randseed`, the random seed to be used in the next step
of the step function, set by 
`~zasim.cagen.nondeterministic.NondeterministicCellLoopMixin`, `activity`, or
`histogram`, set by the `stats classes <zasim.cagen.stats>` or anything else.

.. _tutorial_stepfunc_simulator:

A common interface: the `Simulator`
-----------------------------------

In order for :ref:`displays <display-package>` and `controls
<zasim.gui.control>` to work, there is a unified interface for all kinds of
simulators, wether they are based on a `StepFunc` class and a `Target`, or
any other class you can come up with. This interface is defined and documented
in `zasim.simulator`. There is a special class for a Simulator built from a
`StepFunc` and a `Target`, which is the `~zasim.simulator.CagenSimulator`
and a class for a StepFunc and Target based simulator, that also
offers a rule number, like the elementary cellular automaton would, called
`~zasim.simulator.ElementaryCagenSimulator`.

In fact, the simulators from `zasim.cagen.simulators` are all derived from
either the `ElementaryCagenSimulator` or the `CagenSimulator`.

The `CagenSimulator` and the `ElementaryCagenSimulator` are both constructed
from a `StepFunc` and a `Target`.

The Simulator grants access to the extra attributes of the target via the `t`
property. It is a `~zasim.simulator.TargetProxy` object, that will allow
access to the extra attrs and nothing else.


Signals and Slots
-----------------

The `Simulator` interface offers a couple of signals,
most notably `~zasim.simulator.SimulatorInterface.updated` and
`~zasim.simulator.SimulatorInterface.changed`, which you can connect any python
function or Qt slot to. `updated` will be emitted, when the simulator has made
a step and `changed` will be emitted when the configuration has changed due to
some other event, such as the user drawing on the image. Connecting functions to
those signals works like this::

    >>> from zasim.cagen.simulators import ElementaryCagenSimulator
    >>> sim = ElementaryCagenSimulator(size=(10,), rule=110)
    >>> def fizzbuzz():
    >>>     if sim.step_number % 3 == 0:
    >>>         if sim.step_number % 5 == 0:
    >>>             print "fizzbuzz"
    >>>         else:
    >>>             print "fizz"
    >>>     elif sim.step_number % 5 == 0:
    >>>         print "buzz"
    >>> sim.updated.connect(fizzbuzz)
    >>> sim.step()
    >>> sim.step()
    >>> sim.step()
    fizz
    >>> sim.step()
    >>> sim.step()
    buzz
    >>> # and disconnect the function again
    >>> sim.updated.disconnect(fizzbuzz)

This is how the display classes work: They connect `updated` to
`~zasim.display.console.BaseConsolePainter.after_step` and `changed` to
`~zasim.display.console.BaseConsolePainter.conf_changed`.


Ensuring compatibility
----------------------

Before doing too much, the `StepFunc` constructor will check compatibility
between the StepFuncVisitors. The way this works is, that each StepFuncVisitor
has three properties, that have to be set after bind has been set. Those are:

`provides_features`
    A list of features, that the StepFunc gains through this StepFuncVisitor.

`requires_features`
    A list of features, that this StepFuncVisitor requires the StepFunc to have.

`incompatible_features`
    A list of features, that this StepFuncVisitor can't function with.

The only features, that are not provided by any StepFuncVisitors, but by the
StepFunc itself, are `one_dimension` and `two_dimensions`.

The StepFunc goes through all StepFuncVisitors and adds up the provides_features
into one big set, then goes through all the requires_features and checks if any
are missing and finally goes through the incompatible_features to make sure, 
that none of them are present.

If neither the missing nor the incompatible list have any entries,
normal construction of the StepFunc will continue. Otherwise, a
`~zasim.cagen.compatibility.CompatibilityException` will be raised.


Toying around
-------------

The best way to figure out, what's going on is to just plug a couple different
StepFuncVisitors together and see what comes out. The interesting parts are the
properties `pure_py_code_text` for the generated python code and `code_text`
for the generated C++ code:

.. doctest:: a

    >>> from zasim.cagen import *
    >>> # create a random configuration, base 2, 15 cells wide
    >>> t = Target(size=(15,), base=2)
    >>> a = SimpleStateAccessor()
    >>> # Create a border of constant zeros around the configuration
    >>> b = BorderSizeEnsurer()
    >>> # Calculate the normal elementary cellular automaton number 99
    >>> c = ElementaryCellularAutomatonBase(rule=99)
    >>> # loop over a one-dimensional space
    >>> l = OneDimCellLoop()
    >>> # Take the first neighbour from the right and left
    >>> n = ElementaryFlatNeighbourhood()
    >>> # finally, compose the parts into a whole
    >>> sf = StepFunc(loop=l, accessor=a, neighbourhood=n,
    ...               visitors=[b, c], target=t)
    >>> sf.gen_code()
    >>> print sf.pure_py_code_text
    def step_pure_py(self):
    # from hook init
        result = None
        for pos in self.loop.get_iter():
    # from hook pre_compute
            l = self.acc.read_from(offset_pos(pos, (-1,)))
            m = self.acc.read_from(offset_pos(pos, (0,)))
            r = self.acc.read_from(offset_pos(pos, (1,)))
    # from hook compute
            result = self.target.rule[l, m, r]
    # from hook post_compute
            self.acc.write_to(pos, result)
    # from hook loop_end
    <BLANKLINE>
    # from hook after_step
    <BLANKLINE>
    # from hook finalize
        self.acc.swap_configs()
    <BLANKLINE>

As you can see, the generated python code is divided into multiple sections.
This is due to the way the visitors work. Their visit methods are called in
order, so if they just appended their code, it would come out interleaved, so
instead, there are the sections `init`, `pre_compute`, `compute`,
`post_compute`, `after_step` and `finalize`. Each StepFuncVisitor will call
add_py_code with a section name and a string containing the python code to add
and the StepFunc will correct the indentation of the code and add it to the
given category.

The C++ code, that gets generated works the same way, although the sections are
not the same.

Using a wrong combination of StepFuncVisitors will result in such an exception:

.. doctest:: b

    >>> from zasim.cagen import *
    >>> # this time, the configuration is two-dimensional
    >>> t = Target(size=(15,15), base=2)
    >>> a = SimpleStateAccessor()
    >>> # we carelessly forgot to use the correct loop for the two-dimensional
    >>> # config
    >>> l = OneDimCellLoop()
    >>> n = ElementaryFlatNeighbourhood()
    >>> sf = StepFunc(loop=l, accessor=a, neighbourhood=n, target=t)
    Traceback (most recent call last):
    ...
      File "zasim/cagen/stepfunc.py", line 114, in __init__
        raise CompatibilityException(conflicts, missing)
    CompatibilityException: <Compatibility Exception:
        feature conflicts:
    <BLANKLINE>
        missing features:
          (<zasim.cagen.loops.OneDimCellLoop object at 0x31eca90>, ['one_dimension'])
      >

This exception shows, that the OneDimCellLoop misses the feature `one_dimension`.

