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

The package :ref:`zasim.cagen <cagen_package>` offers a variety of
pre-fabricated simulator prototypes with interesting parameters you can
tweak and the :ref:`zasim.display <display-package>` package offers a way to
display each step of the simulator on the console as ascii art - or as images
when using the rich consoles from IPython.

For the simplest of experiments, the `gui <zasim.gui.main>` or the commandline
interface of the `cagen <zasim.cagen.main>` module can be used.

For more complex experiments, you would usually want to create a whole new
python script. The IPython notebook is very good for rapid and exploratory
development of such scripts and can export a runnable python script when it's
complete. Of course, these scripts can use the gui elements of zasim without
problems.


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
   by the `~zasim.cagen` module and pass it to the constructor of
   `~zasim.simulator.CagenSimulator`.

 * `Painter`

   A `Painter` serves to make the state of the `Simulator` visible at each step.
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
a function implemented in `Cython`, C code, that's inlined with `weave`, a
request to some server on your network, ...

But writing the whole step function from scratch for each little experiment
requires a lot of work and makes the whole process less flexible than
it could be.

The `~zasim.cagen` module offers a way out. With it, you can compose a
`Simulator` object from sets of parts that each serve a different purpose.
Those parts are put together into a `~zasim.cagen.stepfunc.StepFunc` object,
which can then be used as a `Simulator` object.

Each of those parts, called `visitors` contributes piece of code to the
`StepFunc` object. There are a few different categories which are later put
together in a template. There's one template for C code and one for python
code.

.. sourcecode:: c

    // C code template
    {localvars} // usually variable declarations for neighbourhood cells
                // and computation
    {loop_begin} // normally one or two nested loops
        {pre_compute} // here, the neighbourhood grabs the values from the
                      // neighbouring cells
        {compute} // here, some result is calculated and stored into the
                  // local variable `result`
        {post_compute} // in this section, the result gets stored.
    {loop_end} // this is usually just closing braces
    {after_step} // here, some additional stuff is done, like storing
                 // histograms and similar things

.. sourcecode:: py

    # python code template
    {init} # local variables are initialized to starting values
    for pos in self.loop.get_iter(): # the iterator is always created the same way.
        {pre_compute} # values from neighbouring cells are read
        {compute} # a computation is done and the local var `result` is written
        {post_compute} # the result value is written
        {loop_end} # things like histograms do their work here
    {after_step} # stats are written etc.
    {finalize} # old and new arrays are swapped


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

Using a `StepFunc` object in a `CagenSimulator` also gives us proper support
for `get_config()` and `set_config()` as well as the step function, all the
signals and a bit more.


Generating Configurations
-------------------------

Oftentimes, the computation is especially interesting with the right starting
configuration. Zasim has a `module <zasim.config>` for generating
configurations from images, ascii files, patterns and probabilities, but since
a configuration is just a numpy array, anything can be used as a data source.

Such a configuration generator object from the config module can be passed as
the `config` option to the constructor of Target and most prefabricated
simulators.

Some cellular automata like those that work like electronic or logic circuits
require a powerful editor for comfortable creation and editing of
configurations. Zasim doesn't strive to offer such a tool. Instead, the
`image import <zasim.config.ImageConfiguration>` config generator and the
`~zasim.display.qt.BaseQImagePainter.export` function of the qt display classes
allow you to use regular graphics programs like `The Gimp` for
your configurations.


Displaying Configurations
-------------------------

Zasim comes with a package called `display`, which has a module for ascii-based
console output and a module for graphical output.

A display will connect to the `updated` signal, that gets emitted by a `Simulator`
whenever the configuration changes and then brings the result to the screen.

The display classes, usually called something ending in `Painter` will generally
use a palette to figure out how to display the configuration. Those can be set in
the `palette_info` dictionary of the Simulator object.

Palettes are always a dictionary from what value is in the configuration to how
it's displayed in the output.

 * colors32, qcolors

   Those are used by the `QImagePainter` to display each cell in the configuration
   as a pixel.

 * tiles

   Those are used by the `TwoDimQImagePalettePainter` to display a little picture
   for each cell.

 * chars

   Those are used by most of the ConsolePainters.

 * hexcolors

   Those are used to display HTML table based representations by the
   ConsolePainters for use in IPython `qtconsole` and `notebook`.

 * cboxes

   Those are used by the `MultiLineOneDimConsolePainter`, which displays more
   than one line per cell. Utility functions in the class allow you to create
   cbox tilesets with ascii-art boxes around the values.

cboxes
======

When not supplying a `cboxes` value in the `palette_info` dictionary of your
Simulator, the `MultiLineOneDimConsolePainter` will create a palette of boxes
based on the `possible_values` list of the Simulator.

Otherwise, you can create a palette by creating one list for each line in the
box as well as an optional list of keys that correspond to each box.

.. sourcecode:: py

    palette = [["foo", "bar", "baz"],
               [" 1 ", " 2 ", " 3 "]]
    values  = [   1,     2,     3  ]

    palette_to_use = MultiLineOneDimConsolePainter.convert_palette(palette, values)

Alternatively, you can directly use the internal format, which is a dictionary
that maps values to a list with one entry per line of the box:

.. sourcecode:: py

    palette = {1: ["foo", " 1 "],
               2: ["bar", " 2 "],
               3: ["baz", " 3 "]}

There is another function that automatically creates ascii-art boxes for
such palettes:

.. sourcecode:: py

    boxed_palette = MultiLineOneDimConsolePainter.box_art_palette(palette)

