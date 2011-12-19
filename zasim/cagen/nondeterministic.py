"""This module offers `CellLoop` classes for nondeterministic step function
execution.

The idea behind this is, that in a physical realisation of a cellular automaton, the
single cells may not update with the exact same frequency, so that the order in
which the cells execute may be arbitrary and asynchronous.

This is formally defined with a probability that decides, for each cell in turn, if
it may update or not.

.. seealso::

    `zasim.cagen.beta_async` implements a different kind of asynchronous
    execution. While the formal definitions are compatible, the implementations
    in nondeterministic should not be mixed with the implementations in
    beta_async.

Implementation details
----------------------

This implementation offers the `NondeterministicCellLoopMixin`, which you can add as
a first base class next to any kind of `CellLoop`. For your convenience, the classes
`OneDimNondeterministicCellLoop` and `TwoDimNondeterministicCellLoop` are already
composed for you.


{LICENSE_TEXT}
"""
from .bases import StepFuncVisitor
from .loops import OneDimCellLoop, TwoDimCellLoop
from .compatibility import random_generator

from random import Random
import numpy as np

class RandomGenerator(StepFuncVisitor):
    """Add this StepFuncVisitor to your stepfunc, so that random generators
    can be used by python and c code in a proper manner. Supply the
    random_generator argument to define the seed, that is used at the
    beginnig.
        .. note::
            The random generator will be used directly by the python code, but
            the C code is a bit more complex.

            The C code carries a randseed with it that gets seeded by the
            Python random number generator at the very beginning, then it uses
            the randseed attribute in the target to seed srand. After the
            computation, randseed will be set to rand(), so that the same
            starting seed will still give the same result.

        .. warning::
            If reproducible randomness sequences are desired, do NOT mix the
            pure python and weave inline step functions!
    """

    provides_features = [random_generator]

    def __init__(self, random_generator=None, **kwargs):
        super(RandomGenerator, self).__init__(**kwargs)

        if random_generator is None:
            self.random = Random()
        else:
            self.random = random_generator

    def visit(self):
        """Add code to C and python """
        super(RandomGenerator, self).visit()

        self.code.add_code("localvars",
                """srand(randseed(0));""")
        self.code.add_code("after_step",
                """randseed(0) = rand();""")
        self.code.attrs.append("randseed")

    def set_target(self, target):
        """Adds the randseed attribute to the target."""
        super(RandomGenerator, self).set_target(target)
        # FIXME how do i get the randseed out without using np.array?
        target.randseed = np.array([self.random.random()])

    def bind(self, code):
        super(RandomGenerator, self).bind(code)
        code.random = self.random

class NondeterministicCellLoopMixin(StepFuncVisitor):
    """Deriving from a CellLoop and this Mixin will cause every cell to be
    skipped with a given probability"""

    probab = 0.5
    """The probability with which to execute each cell."""

    requires_features = [random_generator]

    def __init__(self, probab=0.5, **kwargs):
        """:param probab: The probability of a cell to be computed.
        :param random_generator: If supplied, use this Random object for
                                 random values.
        """

        super(NondeterministicCellLoopMixin, self).__init__(**kwargs)
        self.probab = probab

    def visit(self):
        """Adds C code for handling the skipping."""
        super(NondeterministicCellLoopMixin, self).visit()
        self.code.add_code("loop_begin",
                """if(rand() >= RAND_MAX * NONDET_PROBAB) {
                    %(copy_code)s
                    continue;
                };""" % dict(probab=self.probab,
                    copy_code=self.code.acc.gen_copy_code(),
                    ))

        self.code.add_py_hook("pre_compute", """
            # if the cell isn't executed, just copy instead.
            if self.random.random() >= NONDET_PROBAB:
                %(copy_code)s
                continue""" % dict(probab=self.probab,
                                   copy_code=self.code.acc.gen_copy_py_code()))

    def bind(self, code):
        super(NondeterministicCellLoopMixin, self).bind(code)
        code.consts["NONDET_PROBAB"] = self.probab

    def build_name(self, parts):
        super(NondeterministicCellLoopMixin, self).build_name(parts)
        parts.insert(0, "nondeterministic (%s)" % (self.probab))

class OneDimNondeterministicCellLoop(NondeterministicCellLoopMixin,OneDimCellLoop):
    """This Nondeterministic Cell Loop loops over one dimension, skipping cells
    with a probability of probab."""
    pass

class TwoDimNondeterministicCellLoop(NondeterministicCellLoopMixin, TwoDimCellLoop):
    """This Nondeterministic Cell Loop loops over two dimensions, skipping cells
    with a probability of probab."""
    pass
