from .target import TestTarget
from .computations import ElementaryCellularAutomatonBase
from .beta_async import BetaAsynchronousAccessor, BetaAsynchronousNeighbourhood
from .accessors import SimpleStateAccessor
from .nondeterministic import LinearNondeterministicCellLoop
from .loops import LinearCellLoop
from .border import SimpleBorderCopier, BorderSizeEnsurer
from .stats import SimpleHistogram, ActivityRecord
from .neighbourhoods import ElementaryFlatNeighbourhood
from .stepfunc import WeaveStepFunc


class BinRule(TestTarget):
    """A Target plus a WeaveStepFunc for elementary cellular automatons."""

    rule = None
    """The number of the elementary cellular automaton to simulate."""

    def __init__(self, size=None, nondet=1, histogram=False, activity=False, rule=None, config=None, beta=1, copy_borders=True, **kwargs):
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
        super(BinRule, self).__init__(size, config, **kwargs)

        self.rule = None
        self.computer = ElementaryCellularAutomatonBase(rule)

        if beta != 1 and nondet == 1:
            acc = BetaAsynchronousAccessor(beta)
            neighbourhood = ElementaryFlatNeighbourhood(Base=BetaAsynchronousNeighbourhood)
        elif beta == 1:
            acc = SimpleStateAccessor()
            neighbourhood = ElementaryFlatNeighbourhood()
        elif beta != 1 and nondet != 1:
            raise ValueError("Cannot have beta asynchronism and deterministic=False.")

        self.stepfunc = WeaveStepFunc(
                loop=LinearCellLoop() if nondet == 1.0 else
                     LinearNondeterministicCellLoop(probab=nondet),
                accessor=acc,
                neighbourhood=neighbourhood,
                extra_code=[SimpleBorderCopier() if copy_borders else
                            BorderSizeEnsurer(),
                    self.computer] +
                ([SimpleHistogram()] if histogram else []) +
                ([ActivityRecord()] if activity else []), target=self)

        self.rule_number = self.computer.rule

        self.stepfunc.gen_code()

    def step_inline(self):
        """Use the step function to step with weave.inline."""
        self.stepfunc.step_inline()

    def step_pure_py(self):
        """Use the step function to step with pure python code."""
        self.stepfunc.step_pure_py()

    def pretty_print(self):
        return self.computer.pretty_print()

    def __str__(self):
        return str(self.stepfunc)
