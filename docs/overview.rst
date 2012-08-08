.. _overview:

Overview over Zasim
===================

`zasim` is, at heart, a package of useful utilities and parts and pieces to
experiment with cellular automata. For experimentation, an interactive
console is a good tool to find out what zasim offers and to experiment with
different step functions.

There is additional support for running zasim with the new `IPython`
version 0.11 or higher, which offers a "rich" console and a web application
called "notebook". Using the `ipython qtconsole`, images from the cellular
automaton can be displayed directly inside the console as pictures, rather
than ascii art.

The package :mod:`zasim.cagen` offers a variety of pre-fabricated
simulator prototypes with interesting parameters you can tweak and the
:mod:`zasim.display` package offers a way to display each step of the
simulator on the console as ascii art - or as images when using the rich
consoles from IPython.

High-Level Concepts
-------------------

There are a core concepts and pieces that come together in `zasim`:

 * `Simulator`

   A `Simulator` object is any object that offers at least a `step()`
   function to advance computation, a `get_config()` function to get a
   displayable configuration and an `updated` signal, that makes the rest
   of the program aware, that a change has taken place.

   You can base your own `Simulator` object from
   `~zasim.simulator.SimulatorInterface` and implement the functions
   manually, use a pre-made simulator from `~zasim.cagen.simulators` or
   assemble a `~zasim.cagen.stepfunc.StepFunc` object from pieces offered
   by the `~zasim.cagen` module.

 * `Painter`

   A `Painter` serves to make the state of the Simulator visible at each step.
   It listens to the `updated` signal from a Simulator and uses `get_config()`
   to retrieve a configuration, which is then displayed to the user in some
   form.

   Zasim comes with a few Painters in the `zasim.display.console` module,
   which output a character per cell, or an ascii art box for each cell and
   also a few Painters in the `zasim.display.qt` module, which display
   configurations with colors or images for cells, or which display histograms.

 * `Target`

   The `Target` serves as a separate class to hold any data relevant to the
   global state. While the `Simulator` holds a myriad of information, like what
   colors or tiles to use to display the configuration, the `Target` holds
   the current global configuration, states of random number generators, etc.

   Essentially, everything that would be needed to reset a `Simulator` to an
   earlier state or what would be saved away for being resumed later would go
   in the `Target`.

Jigsaw Puzzle: The `cagen` module
---------------------------------

Zasim itself doesn't care how the `step()` function is implemented. You can
write global step functions in a lot of different ways, like a pure python loop
that goes over all cells, a class or function from a `CPython extension module`,
a function implemented in `Cython`, C code, that's in lined with `weave`, a
request to some server on your network, ...

But writing the whole step function from scratch for each little experiment
requires a lot of work and makes the whole process less flexible.

The `cagen` module offers a way out. With it, you can compose a `Simulator`
object from sets of parts that each serve a different purpose. Those
parts are put together into a `StepFunc` object, which can then be used as
a `Simulator` object.

The different parts are sufficiently weakly coupled, so that most parts can
be replaced with other parts that already exist or with parts written for a
specific purpose.

Some examples for this include:

 * Replacing the Loop with a `NondeterministicCellLoop`, so that not every cell
   does a transition on every step.

 * Replacing the `BorderHandler` with a `BorderCopier`, that will turn the
   cell grid into a torus.

 * Adding a `Histogram` from the `~zasim.cagen.stats` module to count changes
   in cell values over time.

The computation the loop is supposed to carry out - Game of Life would be one
example - would be implemented in a `Computation` class, that relies on the
different components of the `StepFunc` to do its work. Examples for this
include asking the `Neighbourhood` how many fields are to be looked at and where
they are or asking the `Accessor` how to store and retrieve data from the
cell configuration.

Using a `StepFunc` object also gives us proper support for `get_config()` and
`set_config()` as well as the step function, all the signals and a bit more.
