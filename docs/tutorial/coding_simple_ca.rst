Programming simple CA interactively
===================================

zasim is, at heart, a package of useful utilities and parts and pieces to
experiment with cellular automata. For experimentation, an interactive
console is a good tool to find out what zasim offers and to experiment with
different step functions.

There is additional support for running zasim with the new `IPython`
version 0.11 or higher, which offers a "rich" console and a web application
called "notebook". Using the ipython qtconsole, images from the cellular
automaton can be displayed directly inside the console as pictures, rather
than ascii art.

The package :mod:`zasim.cagen` offers a variety of pre-fabricated
simulator prototypes with interesting parameters you can tweak and the
:mod:`zasim.display` package offers a way to display each step of the
simulator on the console as ascii art - or as images when using the rich
consoles from IPython.

Starting out: 1d CA
-------------------

Starting out with zasim is quite easy. First, open up your favorite
interactive console, be it the vanilla python interpreter, bpython, IPython
or anything else. You can then go on and import the `~zasim.cagen` package
from zasim and the `~zasim.display.console` module from the display
package. In order to create our own starting configuration, we also need
`numpy`, which is usually imported under the name "np".

.. doctest:: a

    >>> from zasim import cagen
    >>> from zasim.display.console import LinearConsolePainter
    >>> import numpy as np

The most interesting classes for now are
`zasim.cagen.simulators.ElementarySimulator` and
`zasim.display.console.LinearConsolePainter`. The first one is simply a
class for one- or twodimensional elementary cellular automata - in this
case this just refers to cellular automata that are identified by the
used neighbourhood and a rule number - and the second one is a class that
displays the contents of the simulators configuration space as ascii art.

In order to set up a simulator, all we need is to instantiate an
`ElementarySimulator` object. It will take at least the rule number and
either a size to be used for a random configuration or the configuration as
a numpy array. In this case we will create a known configuration. In order
to display it, too, we can create a `LinearConsolePainter` and pass the
simulator as the first argument. It will then, by default, automatically
print out every step that happens in the simulator on the console.

We will just go ahead and choose rule 126, which will paint a sierpinski
triangle. As starting configuration we use a single one surrounded by lots
of zeros. The code looks like this:

.. testsetup:: a

    from zasim import cagen
    from zasim.display.console import LinearConsolePainter
    import numpy as np

.. doctest:: a
    :options: +NORMALIZE_WHITESPACE

    >>> config = np.array([0] * 30 + [1] + [0] * 30)
    >>> sim = cagen.ElementarySimulator(config=config, rule=126)
    >>> disp = LinearConsolePainter(sim, lines=1)
                                  #
    >>> sim.step()
                                 ###
    >>> sim.step()
                                ## ##

As you can see, the config gets printed once when the display object is
created and then after each step. The same goes for stepping in a loop:

.. doctest:: a
    :options: +NORMALIZE_WHITESPACE

    >>> for i in range(10): sim.step()
    ... 
                               #######
                              ##     ##
                             ####   ####
                            ##  ## ##  ##
                           ###############
                          ##             ##
                         ####           ####
                        ##  ##         ##  ##
                       ########       ########
                      ##      ##     ##      ##

Now to explain the lines, one by one::

    >>> config = np.array([0] * 30 + [1] + [0] * 30)

This simply creates a numpy array from thirty zeros, one one and another 30
zeros. This will give us a prettier picture than the random configuration
we would have gotten, had we supplied the size argument, rather than a
configuration.

::

    >>> sim = cagen.ElementarySimulator(config=config, rule=126)

The `~zasim.cagen.ElementarySimulator` takes as arguments the configuration
to use or a size, if the config should be randomly created, as well as a
rule number and then some extra options that are not interesting to us
right now. Those are almost the same as the one you can supply on the
commandline to the `zasim.cagen.main` module.

In this case we create such a simulator from the config we built and set
the rule number to use to 126.

::

    >>> disp = LinearConsolePainter(sim, lines=1)

The `~zasim.display.console.LinearConsolePainter` takes as first argument
the simulator to take configurations from and the `lines` keyword argument
controls how many lines are to be stored in the display. For interactive
console use, 1 is a good value, because otherwise, after each step, the
`LinearConsolePainter` would print out its complete data.

Each call to sim.step will afterwards run the step function on
the configuration and signal all connected displays - in this
case just the `display`. Since we supplied the default value for
`LinearConsolePainter` while constructing it, it has `connect` and
`auto_output` set to true. The `connect` parameter tells the display
to directly connect to the `~zasim.simulator.Simulator.changed` and
`~zasim.simulator.Simulator.updated` signals of the simulator. The other
tells the display to output its data after every change.


IPython interactivity helpers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you use the new IPython with qtconsole or the notebook web-app, you can
also display configurations in-line, right inside the applications, as
images or HTML. This is how that works:

For a html-based display, you can just set `auto_output` for the
`LinearConsolePainter` to false and display the configuration like this::

    >>> disp
    [the configuration would be displayed here]

This does not work in functions or loops, however, because it relies on the
interpreter automatically displaying the representation of any value that
is not caught. If you want to force the display, you can just import the
display function from IPython directtly::

    >>> from IPython.core.display import display
    >>> display(disp)
    [the configuration would be displayed here]

If you want to show the config as a picture, rather than an HTML table,
you can use the LinearQImagePainter instead, which works much like the
LinearConsolePainter::

    >>> from zasim.display.qt import LinearQImagePainter
    >>> disp = LinearQImagePainter(sim, lines=50, scale=4)
    >>> disp
    [the configuration would be displayed here]

For a QImage based painter, it is much more sensible to use a higher
`lines` value, because this way, the image would be a bit bigger. Note
though, that the position the configuration is painted to travels downwards
and is wrapped from the bottom back up to the top, so sometimes you will
see the current configuration in the middle, older values above and even
older values directly below.


The Game of Life - 2d CAs
-------------------------

Although the `ElementarySimulator` supports 2d configurations as well, the
`Game of Life simulator <zasim.cagen.simulators.GameOfLife>` is much nicer
to look at in general. For our next adventure, we instantiate a GameOfLife
and the matching `~zasim.display.console.TwoDimConsolePainter`.

.. doctest:: b

    >>> from zasim import cagen
    >>> from zasim.display.console import TwoDimConsolePainter
    >>> import numpy as np

The most symbolic figure of Game of Life is probably the glider. We will
create an empty configuration and paste a glider into it, as well as an
obstacle for it to collide with:

.. doctest:: b
    :options: +NORMALIZE_WHITESPACE

    >>> config = np.zeros((6, 10), dtype=int)
    >>> config[0:3,0:3] = np.array([
    ...    [0,1,0],
    ...    [0,0,1],
    ...    [1,1,1]])
    >>> config[3:6, 9] = [1, 1, 1]
    >>> config
    array([[0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
           [0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
           [1, 1, 1, 0, 0, 0, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
           [0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
           [0, 0, 0, 0, 0, 0, 0, 0, 0, 1]])

And now we can put the configuration into the simulator, like this:

.. doctest:: b
    :options: +NORMALIZE_WHITESPACE

    >>> sim = cagen.GameOfLife(config=config)
    >>> disp = TwoDimConsolePainter(sim)
     #
      #
    ###
             #
             #
             #

Stepping a few times will show the typical glider movement.
