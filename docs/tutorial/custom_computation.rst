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
    # initialise sup and second_sup to be the bigger and smaller of the first
    # two values
    sup = max(l, m)
    second_sup = min(l, m)

    # go through all the rest of the values
    for val in [r]:
        # push down sup to second_sup or replace second_sup if val is bigger
        if val > sup:
            second_sup, sup = sup, val
        elif val > second_sup:
            second_sup = val
    # the second-biggest number is our new value for the cell.
    result = second_sup

And the class that generates this could look like this:

.. testcode:: a

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
                    """
                    for val in [%(names)s]:
                        if val > sup:
                            second_sup, sup = sup, val
                        elif val > second_sup:
                            second_sup = val""" % dict(
                                names=",".join(self.code.neigh.names[2:])))
            # and finally, set the result value to be second_sup
            self.code.add_py_hook("compute",
                """result = second_sup""")

Now we can feed that into a StepFunc and see what happens.

.. testcode:: a

    from zasim.cagen import *
    import numpy as np
    t = TestTarget(config=np.array([3, 2, 5, 0, 1, 3, 4, 6, 5, 1, 2, 4, 4, 3, 3]),
        base=7)
    a = SimpleStateAccessor()
    b = BorderSizeEnsurer()
    l = LinearCellLoop()
    n = ElementaryFlatNeighbourhood()

    # use our silly computation from above
    c = SillyComputation()

    sf = StepFunc(loop=l, accessor=a, neighbourhood=n,
                  extra_code=[b, c], target=t)
    sf.gen_code()
    print sf.pure_py_code_text

And this is the generated python code::

    def step_pure_py(self):
    # from hook init
        result = None
        sizeX = 15
        for pos in self.loop.get_iter():
    # from hook pre_compute
            l = self.acc.read_from(offset_pos(pos, (-1,)))
            m = self.acc.read_from(offset_pos(pos, (0,)))
            r = self.acc.read_from(offset_pos(pos, (1,)))
    # from hook compute
            sup = max(l, m)
            second_sup = min(l, m)

            for val in [r]:
                if val > sup:
                    second_sup, sup = sup, val
                elif val > second_sup:
                    second_sup = val
            result = second_sup
    # from hook post_compute
            self.acc.write_to(pos, result)
    # from hook after_step

    # from hook finalize
        self.acc.swap_configs()

.. testoutput:: a
    :options: +NORMALIZE_WHITESPACE
    :hide:

    def step_pure_py(self):
    # from hook init
        result = None
        sizeX = 15
        for pos in self.loop.get_iter():
    # from hook pre_compute
            l = self.acc.read_from(offset_pos(pos, (-1,)))
            m = self.acc.read_from(offset_pos(pos, (0,)))
            r = self.acc.read_from(offset_pos(pos, (1,)))
    # from hook compute
            sup = max(l, m)
            second_sup = min(l, m)

            for val in [r]:
                if val > sup:
                    second_sup, sup = sup, val
                elif val > second_sup:
                    second_sup = val
            result = second_sup
    # from hook post_compute
            self.acc.write_to(pos, result)
    # from hook after_step

    # from hook finalize
        self.acc.swap_configs()

As you can see, the code was successfully inserted. Let's see what it does!

.. doctest:: a

    >>> from zasim.simulator import CagenSimulator
    >>> from zasim.display.console import LinearConsolePainter
    >>> sim = CagenSimulator(sf, t)
    >>> disp = LinearConsolePainter(sim, lines=1)
    ;-^ #;,+^#-,,;;
    >>> sim.step_pure_py()
    -;-##;,^^--,,;;
    >>> sim.step_pure_py()
    ---##;,^^--,,;;
    >>> sim.step_pure_py()
    ---##;,^^--,,;;

Apparently, this yields a stable configuration soon. Well, that was interesting!

The one thing, that's still missing is generated C code. It would probably look
something like this::

    # we need at least the sup and second_sup variables
    self.code.add_code("localvars",
        """int sup, second_sup;""")
    # initialise sup and second_sup from the first two neighbourhood cells
    self.code.add_code("compute",
        """
        if (%(name_one)s > %(name_two)s) {
            sup = %(name_one)s;
            second_sup = %(name_two)s;
        } else {
            sup = %(name_two)s;
            second_sup = %(name_one)s;
        }""" % dict(name_one=self.code.neigh.names[0],
                    name_two=self.code.neigh.names[1]))
    # if we have more neighbours, we simply loop over them
    if len(self.code.neigh.names) > 2:
        # in order to loop over the values in C, we create an array from them
        # the C compiler will probably completely optimise this away.
        self.code.add_code("localvars",
            """int neigh_arr[%d]; int neigh_idx;""" % (len(self.code.neigh.names) - 2))
        self.code.add_code("compute",
            """neigh_arr = {%s};""" % (", ".join(self.code.neigh.names[2:])))
        self.code.add_code("compute",
            """
            for (neigh_idx = 0; neigh_idx < %(size)d; neigh_idx++) {
                if (neigh_arr[neigh_idx] > sup) {
                    second_sup = sup;
                    sup = neigh_arr[neigh_idx];
                } else if (neigh_arr[neigh_idx] > second_sup) {
                    second_sup = neigh_arr[neigh_idx];
                }
            }""" % dict(size=len(self.code.neigh.names) - 2))
    self.code.add_code("compute",
       """result = second_sup;""")

