from ..features import HAVE_TUPLE_ARRAY_INDEX

from random import Random
from itertools import product

import numpy as np

class TestTarget(object):
    """The TestTarget is a simple class that can act as a target for a
    :class:`StepFunc`."""

    cconf = None
    """The current config the cellular automaton works on."""

    nconf = None
    """During the step, this is the 'next configuration', otherwise it's the
    previous configuration, because nconf and cconf are swapped after steps."""

    possible_values = (0, 1)
    """What values the cells can have."""

    def __init__(self, size=None, config=None, base=2, **kwargs):
        """:param size: The size of the config to generate. Alternatively the
                        size of the supplied config.
           :param config: Optionally the config to use.
           :param base: The base of possible values for the target.
        """
        super(TestTarget, self).__init__(**kwargs)
        self.possible_values = tuple(range(base))
        if config is None:
            assert size is not None
            try:
                self.cconf = np.zeros(size, np.dtype("i"))
            except TypeError:
                # pypy can't make zeros with tuples as size arg yet.
                # the patch to pypy is awaiting review/merge
                assert len(size) == 1
                self.cconf = np.zeros(size[0], np.dtype("i"))
            rand = Random()
            if HAVE_TUPLE_ARRAY_INDEX:
                for pos in product(*[range(siz) for siz in size]):
                    self.cconf[pos] = rand.choice(self.possible_values)
            else:
                if len(size) != 1:
                    raise NotImplementedError("Can only create random configs"\
                            "in %dd with HAVE_TUPLE_ARRAY_INDEX." % len(size))
                for pos in range(size[0]):
                    self.cconf[pos] = rand.choice(self.possible_values)
            self.size = size
        else:
            self.cconf = config.copy()
            self.size = self.cconf.shape

    def pretty_print(self):
        """pretty-print the configuration and such"""
