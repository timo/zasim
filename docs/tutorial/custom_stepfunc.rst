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

The job of the `StepFunc` object is to make sure the single `StepFuncVisitor`
objects you decide to throw into the blender all play nice together or, if they
won't, report incompatibilities.

It has pre-set slots for a few different types of `StepFuncVisitor` objects,
each contributing a different kind of functionality, but with a somewhat fixed
interface. Those slots are:

 * A `~zasim.cagen.bases.CellLoop` instance (as the `loop` keyword
   argument) decides, what cells have to be considered for the step and in
   what order. Here are some examples of `CellLoop` classes that are already
   there:

   - `~zasim.cagen.loops.LinearCellLoop` and `~zasim.cagen.loops.TwoDimCellLoop`
     loop over all cells in the configuration.

   - `~zasim.cagen.nondeterministic.LinearNondeterministicCellLoop`
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

 * A `~zasim.cagen.bases.BorderHandler` instance (in the `extra_code` list),
   that does things like copying the borders from the sides and at the same
   time ensuring the size of the configuration storage is big enough to keep
   those extra cells. It could also do things like set the border cells to
   changing values or anything you could think of.

 * A `~zasim.cagen.bases.ExtraStats` instance (in the `extra_code` list, as
   well), which gathers some additional statistics about the step function
   execution. The following two `ExtraStats` classes are already available:

   - `~zasim.cagen.stats.SimpleHistogram` counts, how many cells have each
     possible value.

   - `~zasim.cagen.stats.ActivityRecord` counts, how many cells have changed
     their value in one step.

 * Finally, a `~zasim.cagen.bases.Computation` instance (in the `extra_code`
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
