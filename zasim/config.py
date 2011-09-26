"""This module implements different ways to create configurations.

The idea behind the API is, to let the user set any settings in the constructor
of any InitialConfiguration instance and to let the Target instance pass a size
hint and datatype when generating the config.

This way, the Target doesn't have to know anything about what configuration to
generate and how to do it.

By letting the Target only supply a size_hint, the InitialConfiguration is
allowed to dictate what size the configuration should have. This is important
especially for loading configurations from files.

"""

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
        if len(self.percentages) > self.base:
            raise ValueError("Cannot have more percentage values than values.")

        rest = self.base - len(self.percentages)
        if self.percentages:
            self.cumulative_percentages = [sum(self.percentages[:index + 1]) for index in range(len(self.percentages))]
        else:
            self.cumulative_percentages = [1.0 / self.base]
            rest -= 1

        if self.cumulative_percentages[-1] > 1.0:
            raise ValueError("Probabilities must not add up to more than 1.0")

        rest_percentage = 1.0 - self.cumulative_percentages[-1]

        for number in range(rest):
            self.cumulative_percentages.append(self.cumulative_percentages[-1] + rest_percentage / rest)

        if rest == 0 and self.cumulative_percentages[-1] != 1.0:
            raise ValueError("Probabilities must add up to 1.0")

    def generate(self, size_hint=None, dtype=int):
        if size_hint is None:
            size_hint = (random.randrange(1, 100),)

        size = []
        for entry in size_hint:
            size.append(random.randrange(1, 100) if entry is None else entry)

        randoms = np.random.rand(*size)
        arr = np.zeros(randoms.shape, dtype=np.dtype(dtype))

        for pos in product(*[range(siz) for siz in size]):
            arr[pos] = min(idx for idx, perc in enumerate(self.cumulative_percentages)
                           if randoms[pos] < perc)

        return arr
