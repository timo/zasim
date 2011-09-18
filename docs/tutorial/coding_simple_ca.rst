Programming simple CA interactively
===================================

zasim is, at heart, a package of useful utilities and parts and pieces to
experiment with cellular automata. For experimentation, an interactive
console is a good tool to find out what zasim offers and to experiment with
different step functions.

There is additional support for running zasim with the new `IPython`_
version 0.11 or higher, which offers a "rich" console and a web application
called "notebook". Using the ipython qtconsole, images from the cellular
automaton can be displayed directly inside the console as pictures, rather
than ascii art.

The package `zasim.cagen` offers a variety of pre-fabricated simulator
prototypes with interesting parameters you can tweak and the
`zasim.display` package offers a way to display each step of the simulator
on the console as ascii art - or as images when using the rich consoles
from IPython.

Starting out
------------

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

.. doctest:: a


    >>> config = np.array([0] * 30 + [1] + [0] * 30)
    >>> sim = cagen.ElementarySimulator(config=config, rule=126)
    >>> display = LinearConsolePainter(sim, lines=1)
                                  #                              
    >>> sim.step()
                                 ###                             
    >>> sim.step()
                                ## ##                            

As you can see, the config gets printed once when the display object is
created and then after each step. The same goes for stepping in a loop:

.. doctest:: a

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

Now to explain the lines, one by one.

    >>> config = np.array([0] * 30 + [1] + [0] * 30)

This simply creates a numpy array from thirty zeros, one one and another 30
zeros. This will give us a prettier picture than the random configuration
we would have gotten, had we supplied the size argument, rather than a
configuration.

    >>> sim = cagen.ElementarySimulator(config=config, rule=126)

The `~zasim.cagen.ElementarySimulator` takes as arguments the configuration
to use or a size, if the config should be randomly created, as well as a
rule number and then some extra options that are not interesting to us
right now. Those are almost the same as the one you can supply on the
commandline to the `zasim.cagen.main` module.

In this case we create such a simulator from the config we built and set
the rule number to use to 126.

    >>> display = LinearConsolePainter(sim, lines=1)

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
