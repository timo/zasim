"""

"""
# This file is part of zasim. zasim is licensed under the BSD 3-clause license.
# See LICENSE.txt for details.

from ..config import BaseConfiguration, RandomConfiguration

class Target(object):
    """The Target is a simple class that can act as a target for a
    `StepFunc`."""

    cconf = None
    """The current config the cellular automaton works on."""

    possible_values = (0, 1)
    """What values the cells can have."""

    def __init__(self, size=None, config=None, base=2, **kwargs):
        """:param size: The size of the config to generate. Alternatively the
                        size of the supplied config.
           :param config: Optionally the config or config generator to use.
           :param base: The base of possible values for the target.
        """
        super(Target, self).__init__(**kwargs)
        self.possible_values = tuple(range(base))
        if config is None:
            if self.possible_values != tuple(range(len(self.possible_values))):
                raise ValueError("Can only create a random config if possible_values is contiguous")
            gen = RandomConfiguration(base=len(self.possible_values))
            self.cconf = gen.generate(size_hint=size)
            self.size = self.cconf.shape
        elif isinstance(config, BaseConfiguration):
            self.cconf = config.generate(size_hint=size)
            self.size = self.cconf.shape
        else:
            self.cconf = config.copy()
            self.size = self.cconf.shape

    def pretty_print(self):
        """pretty-print the configuration and such"""
