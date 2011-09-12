from .target import TestTarget
from .computations import ElementaryCellularAutomatonBase, LifeCellularAutomatonBase
from .beta_async import BetaAsynchronousAccessor, BetaAsynchronousNeighbourhood
from .accessors import SimpleStateAccessor
from .nondeterministic import LinearNondeterministicCellLoop, TwoDimNondeterministicCellLoop
from .loops import LinearCellLoop, TwoDimCellLoop
from .border import SimpleBorderCopier, TwoDimSlicingBorderCopier, BorderSizeEnsurer
from .stats import SimpleHistogram, ActivityRecord
from .neighbourhoods import ElementaryFlatNeighbourhood, VonNeumannNeighbourhood, MooreNeighbourhood
from .stepfunc import WeaveStepFunc

from ..simulator import ElementaryCagenSimulator, CagenSimulator

class ElementarySimulator(ElementaryCagenSimulator):
    """A :class:`ElementaryCagenSimulator` with a target and stepfunc created
    automatically for the given parameters.

    Set neighbourhood to None and a :class:`ElementaryFlatNeighbourhood`
    will be used if the config is one-dimensional, otherwise a
    :class:`VonNeumannNeighbourhood` will be created. If the rule number
    is out of range for it, a :class:`MooreNeighbourhood` will be used
    instead.

    .. note ::

        If you supply a neighbourhood, that is not based on
        :class:`BetaAsynchronousNeighbourhood`, but set beta to a value other
        than 1, you will get a warning."""

    rule_nr = None
    """The number of the elementary cellular automaton to simulate."""

    rule = None
    """The lookup array corresponding to the rule number."""

    def __init__(self, size=None, nondet=1,
                 histogram=False, activity=False,
                 rule=None, config=None,
                 beta=1, copy_borders=True,
                 neighbourhood=None,
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
           :param neighbourhood: The neighbourhood to use."""
        if size is None:
            size = config.shape

        computer = ElementaryCellularAutomatonBase(rule)
        self.rule_nr = computer.rule
        target = TestTarget(size, config)

        if neighbourhood is None:
            if len(size) == 1:
                neighbourhood_class = ElementaryFlatNeighbourhood
            elif len(size) == 2:
                if rule < 2 ** 32:
                    neighbourhood_class = VonNeumannNeighbourhood
                else:
                    neighbourhood_class = MooreNeighbourhood

        if beta != 1 and nondet == 1:
            acc = BetaAsynchronousAccessor(beta)
            if neighbourhood is None:
                neighbourhood = neighbourhood_class(Base=BetaAsynchronousNeighbourhood)
            elif not isinstance(neighbourhood, BetaAsynchronousNeighbourhood):
                raise ValueError("If you set beta to a value other than 1, you "
                                 "must supply a neighbourhood that is based on "
                                 "BetaAsynchronousNeighbourhood.")
        elif beta == 1:
            acc = SimpleStateAccessor()
            if neighbourhood is None:
                neighbourhood = neighbourhood_class()
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
        self.computer = computer
        stepfunc.gen_code()

        self.rule = target.rule

        super(ElementarySimulator, self).__init__(stepfunc, target, rule)

    def pretty_print(self):
        return self.computer.pretty_print()

BinRule = ElementarySimulator

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
