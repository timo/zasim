from .target import TestTarget
from .computations import ElementaryCellularAutomatonBase, LifeCellularAutomatonBase
from .beta_async import BetaAsynchronousAccessor, BetaAsynchronousNeighbourhood
from .accessors import SimpleStateAccessor
from .nondeterministic import LinearNondeterministicCellLoop, TwoDimNondeterministicCellLoop
from .loops import LinearCellLoop, TwoDimCellLoop
from .border import SimpleBorderCopier, TwoDimSlicingBorderCopier, BorderSizeEnsurer
from .stats import SimpleHistogram, ActivityRecord
from .neighbourhoods import ElementaryFlatNeighbourhood, VonNeumannNeighbourhood, MooreNeighbourhood
from .stepfunc import StepFunc

from ..simulator import ElementaryCagenSimulator, CagenSimulator

import inspect
import numpy as np

def automatic_stepfunc(size=None, config=None, computation=None,
                       nondet=1, beta=1,
                       histogram=False, activity=False,
                       copy_borders=True, neighbourhood=None,
                       base=2, extra_code=None,
                       target_class=TestTarget, **kwargs):
    """From the given parameters, assemble a StepFunc with the given
    computation and extra_code objects. Returns the stepfunc."""
    if size is None and isinstance(config, np.ndarray):
        size = config.shape

    target = target_class(size, config, base=base)
    size = target.size

    if neighbourhood is None:
        if len(size) == 1:
            neighbourhood_class = ElementaryFlatNeighbourhood
        elif len(size) == 2:
            neighbourhood_class = VonNeumannNeighbourhood

    if beta != 1 and nondet == 1:
        acc = BetaAsynchronousAccessor(beta)
        if neighbourhood is None:
            neighbourhood = neighbourhood_class(Base=BetaAsynchronousNeighbourhood)
        elif inspect.isfunction(neighbourhood):
            neighbourhood = neighbourhood(Base=BetaAsynchronousNeighbourhood)
        elif not isinstance(neighbourhood, BetaAsynchronousNeighbourhood):
            raise ValueError("If you set beta to a value other than 1, you "
                             "must supply a neighbourhood that is based on "
                             "BetaAsynchronousNeighbourhood.")
    elif beta == 1:
        acc = SimpleStateAccessor()
        if neighbourhood is None:
            neighbourhood = neighbourhood_class()
        elif inspect.isfunction(neighbourhood):
            neighbourhood = neighbourhood()

    elif beta != 1 and nondet != 1:
        raise ValueError("Cannot have beta asynchronism and deterministic != 1.")

    if len(size) == 1:
        if nondet == 1.0:
            loop = LinearCellLoop()
        else:
            loop = LinearNondeterministicCellLoop(probab=nondet)
    elif len(size) == 2:
        if nondet == 1.0:
            loop = TwoDimCellLoop()
        else:
            loop = TwoDimNondeterministicCellLoop(probab=nondet)

    if copy_borders:
        if len(size) == 1:
            border = SimpleBorderCopier()
        elif len(size) == 2:
            border = TwoDimSlicingBorderCopier()
    else:
        border = BorderSizeEnsurer()

    if extra_code is None:
        extra_code = []

    stepfunc = StepFunc(
            loop=loop,
            accessor=acc,
            neighbourhood=neighbourhood,
            extra_code=[border, computation] +
            ([SimpleHistogram()] if histogram else []) +
            ([ActivityRecord()] if activity else []) +
            extra_code, target=target)

    return stepfunc

class ElementarySimulator(ElementaryCagenSimulator):
    """A `ElementaryCagenSimulator` with a target and stepfunc created
    automatically for the given parameters.

    Set neighbourhood to None and a `ElementaryFlatNeighbourhood`
    will be used if the config is one-dimensional, otherwise a
    `VonNeumannNeighbourhood` will be created. If the rule number
    is out of range for it, a `MooreNeighbourhood` will be used
    instead.

    .. note ::

        If you supply a neighbourhood, that is not based on
        `BetaAsynchronousNeighbourhood`, but set beta to a value other
        than 1, you will get a warning."""

    rule = None
    """The lookup array corresponding to the rule number."""

    def __init__(self, size=None, nondet=1,
                 histogram=False, activity=False,
                 rule=None, config=None,
                 beta=1, copy_borders=True,
                 neighbourhood=None,
                 base=2,
                 **kwargs):
        """:param size: The size of the config to generate if no config
                        is supplied. Must be a tuple.
           :param nondet: If this is not 1, use this value as the probability
                          for each cell to get executed.
           :param histogram: Generate and update a histogram as well?
           :param rule: The rule number for the elementary cellular automaton.
           :param config: Optionally the configuration to use.
           :param beta: If the probability is not 1, use this as the
                        probability for each cell to succeed in exposing its
                        result to the neighbouring cells.
                        This is incompatible with the nondet parameter.
           :param copy_borders: Copy over data from the other side?
           :param neighbourhood: The neighbourhood to use.
           :param base: The base of possible values for the configuration.
           """
        if size is None:
            size = config.shape

        computer = ElementaryCellularAutomatonBase(rule)

        self.computer = computer

        if neighbourhood is None:
            if len(size) > 1:
                if rule is None or rule < base ** (base ** 5):
                    neighbourhood = VonNeumannNeighbourhood
                else:
                    neighbourhood = MooreNeighbourhood
            else:
                neighbourhood = ElementaryFlatNeighbourhood

        stepfunc = automatic_stepfunc(size=size, config=config, computation=computer,
                nondet=nondet, beta=beta,
                histogram=histogram, activity=activity,
                copy_borders=copy_borders, neighbourhood=neighbourhood,
                base=base, extra_code=[])

        target = stepfunc.target
        stepfunc.gen_code()

        self.rule = target.rule
        rule_nr = computer.rule

        super(ElementarySimulator, self).__init__(stepfunc, target, rule_nr)

    def pretty_print(self):
        return self.computer.pretty_print()

BinRule = ElementarySimulator

class GameOfLife(CagenSimulator):
    """A `CagenSimulator` with a target and stepfunc created
    automatically for the given parameters. The supplied life_params are passed
    as keyword arguments to `LifeCellularAutomatonBase`."""
    def __init__(self, size=None, nondet=1,
                 histogram=False, activity=False,
                 config=None,
                 beta=1, copy_borders=True,
                 life_params={},
                 **kwargs):
        """:param size: The size of the config to generate if no config is
                        supplied via the *config* parameter.
           :param nondet: If this is not 1, use this value as the probability
                          for each cell to get executed.
           :param histogram: Generate and update a histogram as well?
           :param config: Optionally the configuration to use.
           :param beta: If the probability is not 1, use this as the
                        probability for each cell to succeed in exposing its
                        result to the neighbouring cells.
                        This is incompatible with the nondet parameter.
           :param copy_borders: Copy over data from the other side?
           :param life_params: Those parameters are passed on to the constructor
                               of `LifeCellularAutomatonBase`."""

        computer = LifeCellularAutomatonBase(**life_params)

        stepfunc = automatic_stepfunc(size=size, config=config, computation=computer,
                nondet=nondet, beta=beta,
                histogram=histogram, activity=activity,
                copy_borders=copy_borders, neighbourhood=MooreNeighbourhood,
                extra_code=[])

        target = stepfunc.target
        stepfunc.gen_code()

        super(GameOfLife, self).__init__(stepfunc, target)

