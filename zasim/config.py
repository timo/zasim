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
# This file is part of zasim. zasim is licensed under the BSD 3-clause license.
# See LICENSE.txt for details.



from __future__ import division

from features import HAVE_NUMPY_RANDOM, HAVE_MULTIDIM

import random
import math
import numpy as np
from itertools import product

class BaseInitialConfiguration(object):
    """This class defines the interface that initial configuration generators
    should have to the outside."""

    def generate(self, size_hint=None, dtype=np.dtype("i")):
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

class BaseRandomInitialConfiguration(BaseInitialConfiguration):
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
            self.cumulative_percentages = [1 / self.base]
            rest -= 1

        if self.cumulative_percentages[-1] > 1.0:
            raise ValueError("Probabilities must not add up to more than 1.0")

        rest_percentage = 1.0 - self.cumulative_percentages[-1]

        for number in range(rest):
            self.cumulative_percentages.append(self.cumulative_percentages[-1] + rest_percentage / rest)

        if rest == 0 and self.cumulative_percentages[-1] != 1.0:
            raise ValueError("Probabilities must add up to 1.0")

    def size_hint_to_size(self, size_hint=None):
        if size_hint is None:
            size_hint = (random.randrange(1, 100),)

        size = []
        for entry in size_hint:
            size.append(random.randrange(1, 100) if entry is None else entry)

        return tuple(size)

    def generate(self, size_hint=None, dtype=np.dtype("i")):
        size = self.size_hint_to_size(size_hint)

        if not HAVE_NUMPY_RANDOM and not HAVE_MULTIDIM:
            # pypy compatibility
            assert len(size) == 1
            randoms = np.array([random.random() for i in xrange(size[0])])
            arr = np.zeros(len(randoms), dtype=dtype)
        elif not HAVE_NUMPY_RANDOM and HAVE_MULTIDIM:
            randoms = np.array([random.random() for i in xrange(reduce(lambda a,b:a*b, size))])
            randoms = randoms.reshape(*size)
            arr = np.zeros(randoms.shape, dtype=dtype)
        else:
            randoms = np.random.rand(*size)
            arr = np.zeros(randoms.shape, dtype=dtype)

        for pos in product(*[xrange(siz) for siz in size]):
            arr[pos] = min(idx for idx, perc in self.cumulative_percentages
                           if randoms[pos] < perc)

        return arr

    def make_percentages_cumulative(self, percentages):
        self.percentages = percentages
        if len(self.percentages) > len(self.values):
            raise ValueError("Cannot have more percentage values than values.")

        rest = len(self.values) - len(self.percentages)
        if self.percentages:
            cumulative_percentages = [sum(self.percentages[:index + 1]) for index in range(len(self.percentages))]
        else:
            cumulative_percentages = [1.0 / len(self.values)]
            rest -= 1

        if cumulative_percentages[-1] > 1.0:
            raise ValueError("Probabilities must not add up to more than 1.0")

        rest_percentage = 1.0 - cumulative_percentages[-1]

        for number in range(rest):
            cumulative_percentages.append(cumulative_percentages[-1] + rest_percentage / rest)

        if rest == 0 and cumulative_percentages[-1] != 1.0:
            raise ValueError("Probabilities must add up to 1.0")

        self.cumulative_percentages = list(zip(self.values, cumulative_percentages))

class RandomInitialConfiguration(BaseRandomInitialConfiguration):
    def __init__(self, base=2, *percentages):
        """Create a random initial configuration with values from 0 to base-1
        inclusive and, if positional arguments are given, use the supplied
        percentages for the different states."""

        self.values = range(base)
        self.make_percentages_cumulative(percentages)

class RandomInitialConfigurationFromPalette(BaseRandomInitialConfiguration):
    def __init__(self, values, *percentages):
        """Create a random initial configuration with the given values and,
        if positional arguments are given, use the supplied
        percentages for the different states."""

        self.values = values
        self.make_percentages_cumulative(percentages)

class AsciiInitialConfiguration(BaseInitialConfiguration):
    """Import an ascii-based file with a palette, as generated by
    `zasim.display.console.BaseConsolePainter.export`."""

    def __init__(self, filename, palette=None):
        """The palette is either a dictionary, mapping value to representation
        or a list with representation values.
        If no palette is supplied, the PALETTE value from BaseConsolePainter is
        used."""

        self.filename = filename
        if not palette:
            from zasim.display import console
            palette = console.PALETTE
        if isinstance(palette, list):
            palette = dict(enumerate(palette))
        self.palette = palette

    def generate(self, size_hint=None, dtype=np.dtype("i")):
        lines = []
        with open(self.filename, "r") as config:
            for line in config:
                lines.append(np.array(list(line.strip("\n"))))
        whole_conf = np.array(lines)
        result = np.empty((len(lines), len(lines[0])), dtype=dtype)
        for value, entry in self.palette.iteritems():
            result[whole_conf == entry] = value
        return result.transpose()

class ImageInitialConfiguration(BaseInitialConfiguration):
    """Import an image file as a configuration."""

    def __init__(self, filename, scale=1, palette=None):
        self.filename = filename

        if palette is None:
            from zasim.display.qt import PALETTE_32
            palette = PALETTE_32
        if isinstance(palette, list):
            palette = dict(enumerate(palette))
        self.palette = palette
        self.scale = scale

    def generate(self, size_hint=None, dtype=np.dtype("i")):
        from .external.qt import QImage
        image = QImage()
        assert image.load(self.filename)
        image = image.convertToFormat(QImage.Format_RGB32)
        if self.scale != 1:
            image = image.scaled(image.width() // self.scale,
                                 image.height() // self.scale)
        nparr = np.frombuffer(image.bits(), dtype=np.uint32)
        nparr = nparr.reshape((image.width(), image.height()), order="F")
        result = np.ones((image.width(), image.height()), dtype=dtype)

        for value, color in self.palette.iteritems():
            result[nparr == color] = value

        return result


def function_of_radius(function, max_dist="diagonal"):
    if max_dist == "shortest":
        calc_max_dist = lambda size: min(size)
    elif max_dist == "longest":
        calc_max_dist = lambda size: max(size)
    elif max_dist == "diagonal":
        def calc_max_dist(size):
            halves = [num / 2 for num in size]
            squares = [num ** 2 for num in halves]
            return math.sqrt(sum(squares))

    def wrapper(*args):
        dists = []
        half = len(args) // 2
        for num in range(half):
            center = args[num + half] / 2
            dists.append(abs(center - args[num]))

        squares = [num ** 2 for num in dists]
        dist = math.sqrt(sum(squares))

        return function(dist, calc_max_dist(args[half:]))

    return wrapper

class DensityDistributedConfiguration(RandomInitialConfiguration):
    """Create a distribution from functions giving the probability for each
    field to have a given value.

    For prob_dist_fun, supply a dictionary with one entry per value you
    want to end up in the configuration as the key. The value is a lambda
    from position and config size to relative probability at that position.

    For each position in the configuration, every function is called and the
    results added up to figure out, what value would be 100% for that cell,
    then the relative probabilities are divided and used for choosing a
    value.

    If a value is an integer, rather than a callable, then it will be
    interpreted as a constant function instead."""

    def __init__(self, prob_dist_fun):
        self.prob_dist_fun = prob_dist_fun

    def generate(self, size_hint=None, dtype=np.dtype("i")):
        size = self.size_hint_to_size(size_hint)

        # XXX remove duplicate code here?
        result = np.zeros(size, dtype)
        if not HAVE_NUMPY_RANDOM and not HAVE_MULTIDIM:
            # pypy compatibility
            assert len(size) == 1
            randoms = np.array([random.random() for i in xrange(size[0])])
        elif not HAVE_NUMPY_RANDOM and HAVE_MULTIDIM:
            randoms = np.array([random.random() for i in xrange(reduce(lambda a,b:a*b, size))])
            randoms = randoms.reshape(*size)
        else:
            randoms = np.random.rand(*size)


        for pos in product(*[xrange(siz) for siz in size]):
            relative_probabs = {}
            for key, func in self.prob_dist_fun.iteritems():
                if isinstance(func, int):
                    relative_probabs[key] = func
                else:
                    relative_probabs[key] = self.prob_dist_fun[key](*(pos + size))

            one = sum(relative_probabs.values())
            cumulative_percentages = {}
            cumulative = 0
            for key, relative_perc in relative_probabs.iteritems():
                part = relative_perc / one
                cumulative_percentages[key] = cumulative + part
                cumulative += part

            # XXX remove duplicate code here?
            result[pos] = min(idx for idx, perc in cumulative_percentages.iteritems()
                           if randoms[pos] < perc)

        return result

