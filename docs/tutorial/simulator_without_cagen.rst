.. _tutorial_simulator_without_cagen:

Creating a simulator without the cagen module
=============================================

In this part of the tutorial, we are going to model a moving tape in a turing
machine using a 1d cellular automaton.


Behavior to model
-----------------

In this model, tape cells have two separate values, a symbol (ranging from a to c)
and optionally a symbol that gets carried to the left. A tape then looks something
like this::

    +==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+
    |a |b |c |c |a |b |a |c |c |a |c |a |b |b |a |a |c |c |a |a |a |a |c |b |a |
    +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
    |  |  |<a|  |  |<a|  |  |  |  |<c|  |  |  |<c|  |  |<c|  |  |  |  |  |  |  |
    +==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+

In every step, a cell and its right neighbour are considered, and the rules for
transmitting are like this::

    +==+          +==+
    | X|          | X|
    +--+--+  -->  +--+
    | ?|  |       |  |
    +==+==+       +==+

    +==+          +==+
    | X|          | Y|
    +--+--+  -->  +--+
    | ?|<Y|       |<X|
    +==+==+       +==+

Implementation
--------------

A clever way to number the states is this one::

    +==+==+==+==+==+==+==+==+==+==+==+==+
    | a| a| a| a| b| b| b| b| c| c| c| c|
    +--+--+--+--+--+--+--+--+--+--+--+--+
    |<a|<b|<c|  |<a|<b|<c|  |<a|<b|<c|  |
    +==+==+==+==+==+==+==+==+==+==+==+==+
     0  1  2  3  4  5  6  7  8  9  10 11

It has the property that the lower two bits and the upper two bits of the state
number encode the upper and lower symbol the same way.

Then, the step function is pretty simple to implement. Assuming our states are in
an array called `self.cconf`, we can use this neat trick to get each cell and its
right neighbour from the array using pythons builtin function `zip`::

    for index, (cell, next_cell) in enumerate(zip(self.cconf[:-1], self.cconf[1:])):

`self.cconf[:-1]` is the array ending on its penultimate cell and `self.cconf[1:]`
is the array starting at its second cell. zip puts each element from both arrays
into a tuple and enumerate adds an index to the front. The elements returned look
like (5, (0, 3)) if the 5th cell is an "a <a" and the 6th cell is an "a".

The first operation we need to do is to move the upper symbol down and moving the
lower symbol up. This can be done with the bit masks `~~3` (all but the lower 2 bits)
and `3` (only the lower two bits). Turning the upper symbol into a lower symbol
is then just a bit-shift operation away, as is turning the lower symbol into an
upper symbol::

    reversed = (value & 3) << 2 | (value & ~3) >> 2

The other operation needed for the step function is to clear the lower two bits,
which is also easy::

    upper_only = value | 3

The full step function is then simply this::

    def step(self):
        for index, (cell, next_cell) in enumerate(zip(self.cconf[:-1], self.cconf[1:])):
            result = cell
            if next_cell & 3 == 3:
                # if the lowest 2 bytes are 1, no information is transferred and
                # the transferal state is cleared
                result = cell | 3
            else:
                # otherwise, the information from the right is moved here
                # and the own information is transferred.
                result = (next_cell & 3) << 2 | (cell & ~3) >> 2

            self.cconf[index] = result

        # notify any listeners, that the simulator has been stepped.
        self.step_number += 1
        self.updated.emit()

In addition to changing the configuration array, we need to emit the `updated`
signal to comply with the `zasim.simulator.BaseSimulator` interface.

Building the Palette
--------------------

In order for the simulator to correctly be displayed, we need to create a palette,
too. `zasim.display.console.MultilineOneDimConsolePainter` can render images to
ascii just like shown above with the right palette. Not creating a custom palette
will give us output like this::

    +==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+
    |11|3 |3 |7 |5 |11|7 |5 |7 |7 |7 |0 |3 |11|3 |7 |5 |3 |11|10|11|11|5 |3 |3 |
    +==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+==+

The code to get such an output is quite simple::

    tape = TuringTapeSimulator()
    painter = MultilineOneDimConsolePainter(tape)

A palette is created for us based on the `possible_values` attribute of the
`target object`. However, a much better palette can easily be created with the
following code::

    palette = [[" a", " a", " a", " a", " b", " b", " b", " b", " c", " c", " c", " c"],
               ["<a", "<b", "<c", "  ", "<a", "<b", "<c", "  ", "<a", "<b", "<c", "  "]]
    # optional: numerical values for each cell
    values  =  [ 0,    1,    2,    3,    4,    5,    6,    7,    8,    9,    10,   11]
    # probabilities for each cell to be in the starting configuration
    probabs =  [0.1,   0,    0,   0.23,  0,  0.1,    0,   0.23,  0,    0,    0.1, 0.24]

    # create ascii art boxes around each palette entry
    palette = MultilineOneDimConsolePainter.box_art_palette(palette)
    # convert the palette into the internal format used by the Painter.
    palette = MultilineOneDimConsolePainter.convert_palette(palette, values)

Creating the Simulator class
----------------------------

Deriving from `~zasim.simulator.BaseSimulator`, a `TuringTapeSimulator` can easily
be created. The first thing to note is, that a few properties are required to exist
in the class, since otherwise other parts of zasim can and will complain.

The most important thing is a `target object`. There is no requirement for the
target object to be a different object, so we can just set it up to be a
`~zasim.simulator.TargetProxy`. We set `cconf` and `possible_values` to be its
`target_attrs`, which are the attributes, that the `TargetProxy` will make
available. This requires a `cconf` to actually exist, so we use the probabilities
list for a `~zasim.config.RandomInitialConfiguration`::

    class TuringTapeSimulator(BaseSimulator):
        def __init__(self):
            # call parents init so that Qt Signals can work
            super(TuringTapeSimulator, self).__init__()

            # set the size of the tape, as per the Simulator interface.
            self.shape = (25,)
            self.cconf = RandomInitialConfiguration(12, *probabs).generate((self.shape))
            # do not send stuff from the right border.
            self.cconf[-1] = self.cconf[-1] | 3

            self.possible_values = values

            self.target_attrs = ["cconf", "possible_values"]

            self.t = TargetProxy(self, self.target_attrs)

        def get_config(self):
            # this is required for Painters to work.
            return self.cconf

Letting a simulation run
------------------------

When the `TuringTapeSimulator` class is done, with its step function from above, it
can be used quite simply::

    tape = TuringTapeSimulator()
    painter = MultilineOneDimConsolePainter(tape, palette, compact_boxes=True)

    painter.after_step()
    print

    for i in range(10):
        tape.step()
        print

Running that code gives us output like this:

.. command-output:: python -m zasim.examples.turing.main

