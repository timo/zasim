"""The compatibility module offers a way for :class:`StepFuncVisitor` objects
to express, what combinations are acceptable and what combinations are going to
break, allowing the constructor of the :class:`WeaveStepFunc` to bail out soon
instead of causing an unexpected result during execution.

Each *StepFuncVisitor* has three attributes:

    - requires_features

      A list of compatibility features, that are required for operation.

    - provides_features

      A list of features, that are offered by this class.

    - incompatible_features

      A list of features that are incompatible with this class.
"""

class CompatibilityException(Exception):
    def __init__(self, conflicts, missing):
        self.conflicts = conflicts
        self.missing = missing

    def __str__(self):
        return "<CompatibilityException(%s, %s)>" % (self.conflicts, self.missing)

class CompatibilityFeature(object):
    pass

one_dimension = "one_dimension"
"""The configuration has one dimension."""

two_dimensions = "two_dimensions"
"""The configuration has two dimensions."""

beta_asynchronism = "beta_asynchronism"
"""In order to have beta-asynchronism, it's necessary to use both the
:class:`BetaAsynchronousNeighbourhood` and the :class:`BetaAsynchronousAccessor`.

This feature ensures that."""

histogram = "histogram"
"""This StepFunc has a histogram."""

activity = "activity"
"""This StepFunc calculates the Activity."""
