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
     <~zasim.cagen.nondeterministic.TwoDimNondeterministicCellLoop>`
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
