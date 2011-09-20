Making up a new computation
===========================

In this section we will take a look at how to create custom StepFuncVisitors.
The goal will be to create a nonsensical new StepFunc, just to find out how that
works.

The plan is to prepopulate the whole configuration with random numbers between
zero and ten and in each step, each cell takes the second-biggest value from
its neighbourhood.

The first step is to figure out, what the computation would in fact look
like. We can just use the code that the `SimpleNeighbourhood` class generates
for us in the `pre_compute` section. It will create local variables for
each of the named neighbourhood cells, such as *l*, *r*, and *m* in the
case of the `~zasim.cagen.neighbourhood.ElementaryFlatNeighbourhood`, but
in order to work with any kind of neighbourhood, we can just read out the
`~zasim.cagen.bases.Neighbourhood.names` of the currently used neighbourhood,
accessible as `self.code.neigh` in our visit method, and use that to generate
code. The code we want to end up with might look something like this::

    # assuming l, m and r being the neighbourhood cells...
    # initialise sup
    sup = max(l, m)
    second_sup = min(l, m)
    for val in [r]:
        if val > sup:
            second_sup, sup = sup, val
        elif val > second_sup:
            second_sup = val
    result = second_sup

And the class that generates this could look like this::

    from zasim.cagen.bases import Computation
    class SillyComputation(Computation):
        def visit(self):
            self.code.add_py_hook("compute",
                """sup = max(%(name_one)s, %(name_two)s)
                second_sup = min(%(name_one)s, %(name_two)s)""" % dict(
                    name_one=self.code.neigh.names[0],
                    name_two=self.code.neigh.names[1]))
            # only create a loop if there are more than the 2 cells.
            if len(self.code.neigh.names) > 2:
                self.code.add_py_hook("compute",
                    """for val in %(names)s:
                        if val > sup:
                            second_sup, sup = sup, val
                        elif val > second_sup:
                            second_sup = val""" % dict(
                                names=self.code.neigh.names[2:]))
            # and finally, set the result value to be second_sup
            self.code.add_py_hook("compute",
                """result = second_sup""")
