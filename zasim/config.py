"""This module implements different ways to create configurations."""

import random
import numpy as np
from itertools import product

class BaseInitialConfiguration(object):
    """This class defines the interface that initial configuration generators
    should have to the outside."""

    def generate(self, size_hint=None, dtype=int):
        """Generate the configuration.

        :param size_hint: What size to generate. This can be None, if the
               generator may choose the dimensionality and sizes of each
               dimension freely, or a tuple containing None or a number for
               each dimension. If one or all of the dimensions are None, their
               size will be decided by the generator.

               The size_hint may be ignored by the generator for cases like
               loading a configuration from a file.
        :param dtype: The `~numpy.dtype` to use for the array.
        :returns: A numpy array to be used as the configuration.
        """

class RandomInitialConfiguration(BaseInitialConfiguration):
    def __init__(self, base=2, *percentages):
        """Create a random initial configuration with values from 0 to base-1
        inclusive and, if positional arguments are given, use the supplied
        percentages for the different states."""

        self.base = base
        self.percentages = percentages

    def generate(self, size_hint=None, dtype=int):
        if size_hint is None:
            size_hint = (random.randrange(1, 100),)

        size = []
        for entry in size_hint:
            size.append(random.randrange(1, 100) if entry is None else entry)

        randoms = np.random.rand(*size)
        arr = np.zeros(randoms.size, dtype=np.dtype(dtype))

        rest = self.base - len(self.percentages)
        if self.percentages:
            cumulative_percentages = [sum(self.percentages[:index + 1]) for index in range(len(self.percentages))]
        else:
            cumulative_percentages = [1.0 / self.base]

        rest_percentage = 1.0 - cumulative_percentages[-1]
        for number in range(rest):
            cumulative_percentages.append(cumulative_percentages[-1] + rest_percentage / rest)

        for pos in product(*[range(siz) for siz in size]):
            arr[pos] = min(idx for idx, perc in enumerate(cumulative_percentages)
                           if randoms[pos] < perc)

        return arr
