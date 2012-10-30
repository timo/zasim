"""

"""
# This file is part of zasim. zasim is licensed under the BSD 3-clause license.
# See LICENSE.txt for details.

from .. import config

class Target(object):
    """The Target is a simple class that can act as a target for a
    `StepFunc`."""

    cconf = None
    """The current config the cellular automaton works on."""

    _reset_size = None
    """If a generator was passed as config, this holds the size of
    new configurations to generate when a reset is called."""

    _reset_generator = None
    """If a generator was passed as config, this holds that generator."""

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
            gen = config.RandomConfiguration(base=len(self.possible_values))
            self.cconf = gen.generate(size_hint=size)
            self.size = self.cconf.shape

            self._reset_generator = gen
            self._reset_size = self.size
        elif isinstance(config, config.BaseConfiguration):
            self._reset_generator = config
            self._reset_size = size
            self.cconf = config.generate(size_hint=size)
            self.size = self.cconf.shape
        else:
            self.cconf = config.copy()
            self.size = self.cconf.shape

    def pretty_print(self):
        """pretty-print the configuration and such"""
        # FIXME what was this supposed to be?

class SubCellTarget(Target):
    """The SubCellTarget can act as a target for a`StepFunc` and offers
    multiple subcells."""

    _reset_size = None
    """If a generator was passed as config, this holds the size of
    new configurations to generate when a reset is called."""

    _reset_generators = {}
    """If a generator was passed as config, this holds that generator."""

    possible_values = {}
    """What values the cells in subcells can have."""

    def __init__(self, sets={}, size=None, strings=[], configs={}, **kwargs):
        """:param size: The size of the config to generate. Alternatively the
                        size of the supplied config.
           :param sets: A dictionary of field name to possible values.
           :param strings: What strings exist in the configuration.
           :param configs: A dictionary of field name to configuration array
                           or a configuration generator.
        """
        self.possible_values = sets
        self.fields = list(sets.keys())
        self.strings = strings
        self.stringy_subcells = [k for k, v in self.possible_values.iteritems() if isinstance(v[0], basestring)]

        for key in self.fields:
            if key in self.stringy_subcells:
                self.possible_values[key] = [
                        self.strings.find(value)
                        for value in self.possible_values[key]]

            if key not in configs or configs[key] is None:
                gen = config.RandomConfigurationFromPalette(self.possible_values[key])
                theconf = gen.generate(size_hint=size or self.size)
                size = self.cconf.shape
                self.size = size

                self._reset_generators[key] = gen
                self._reset_size = self.size
            elif isinstance(configs[key], config.BaseConfiguration):
                theconf = config.generate(size_hint=size)
                self._reset_generators[key] = configs[key]
                self._reset_size = size
                if size is not None and size != theconf.shape:
                    raise ValueError("Size mismatch: %s - %s" % size, theconf.shape)
                else:
                    self.size = size
            else:
                theconf = config.copy()
                self.size = theconf.shape
                if size is not None and size != theconf.shape:
                    raise ValueError("Size mismatch: %s - %s" % size, theconf.shape)
                else:
                    self.size = size

            setattr(self, "cconf_%s" % key, theconf)

