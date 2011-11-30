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
lower symbol up. This can be done with the bit masks `~3` (all but the lower 2 bits)
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
        self.updated.emit()

In addition to changing the configuration array, we need to emit the `updated`
signal to comply with the `zasim.simulator.BaseSimulator` interface.
