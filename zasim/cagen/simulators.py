from .target import TestTarget
from .computations import ElementaryCellularAutomatonBase, LifeCellularAutomatonBase
from .beta_async import BetaAsynchronousAccessor, BetaAsynchronousNeighbourhood
from .accessors import SimpleStateAccessor
from .nondeterministic import LinearNondeterministicCellLoop, TwoDimNondeterministicCellLoop
from .loops import LinearCellLoop, TwoDimCellLoop
from .border import SimpleBorderCopier, TwoDimSlicingBorderCopier, BorderSizeEnsurer
from .stats import SimpleHistogram, ActivityRecord
from .neighbourhoods import ElementaryFlatNeighbourhood, MooreNeighbourhood
from .stepfunc import WeaveStepFunc

from ..simulator import ElementaryCagenSimulator, CagenSimulator

class BinRule(ElementaryCagenSimulator):
    """A :class:`ElementaryCagenSimulator` with a target and stepfunc created
    automatically for the given parameters."""

    rule = None
    """The number of the elementary cellular automaton to simulate."""

    def __init__(self, size=None, nondet=1,
                 histogram=False, activity=False,
                 rule=None, config=None,
                 beta=1, copy_borders=True,
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
           :param copy_borders: Copy over data from the other side?"""
        if size is None:
            size = config.shape

        computer = ElementaryCellularAutomatonBase(rule)
        rule = computer.rule
        target = TestTarget(size, config)

        if beta != 1 and nondet == 1:
            acc = BetaAsynchronousAccessor(beta)
            neighbourhood = ElementaryFlatNeighbourhood(Base=BetaAsynchronousNeighbourhood)
        elif beta == 1:
            acc = SimpleStateAccessor()
            neighbourhood = ElementaryFlatNeighbourhood()
        elif beta != 1 and nondet != 1:
            raise ValueError("Cannot have beta asynchronism and deterministic=False.")

        stepfunc = WeaveStepFunc(
                loop=LinearCellLoop() if nondet == 1.0 else
                     LinearNondeterministicCellLoop(probab=nondet),
                accessor=acc,
                neighbourhood=neighbourhood,
                extra_code=[SimpleBorderCopier() if copy_borders else
                                BorderSizeEnsurer(),
                            computer] +
                ([SimpleHistogram()] if histogram else []) +
                ([ActivityRecord()] if activity else []), target=target)
        stepfunc.gen_code()

        super(BinRule, self).__init__(stepfunc, target, rule)

    def pretty_print(self):
        return self.computer.pretty_print()

class GameOfLife(CagenSimulator):
    """A :class:`CagenSimulator` with a target and stepfunc created
    automatically for the given parameters. The supplied life_params are passed
    as keyword arguments to :class:`LifeCellularAutomatonBase`."""
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
                               of :class:`LifeCellularAutomatonBase`."""
        if size is None:
            size = config.shape

        computer = LifeCellularAutomatonBase(**life_params)
        target = TestTarget(size, config)

        if beta != 1 and nondet == 1:
            acc = BetaAsynchronousAccessor(beta)
            neighbourhood = MooreNeighbourhood(Base=BetaAsynchronousNeighbourhood)
        elif beta == 1:
            acc = SimpleStateAccessor()
            neighbourhood = MooreNeighbourhood()
        elif beta != 1 and nondet != 1:
            raise ValueError("Cannot have beta asynchronism and deterministic=False.")

        stepfunc = WeaveStepFunc(
                loop=TwoDimCellLoop() if nondet == 1.0 else
                     TwoDimNondeterministicCellLoop(probab=nondet),
                accessor=acc,
                neighbourhood=neighbourhood,
                extra_code=[TwoDimSlicingBorderCopier() if copy_borders else
                                BorderSizeEnsurer(),
                            computer] +
                ([SimpleHistogram()] if histogram else []) +
                ([ActivityRecord()] if activity else []), target=target)
        stepfunc.gen_code()

        super(GameOfLife, self).__init__(stepfunc, target)
