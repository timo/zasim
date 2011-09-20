"""The compatibility module offers a way for `StepFuncVisitor` objects
to express, what combinations are acceptable and what combinations are going to
break, allowing the constructor of the `StepFunc` to bail out soon
instead of causing an unexpected result during execution.

Each `StepFuncVisitor` has three attributes:

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

beta_async_neighbourhood = "beta_async_neighbourhood"
beta_async_accessor = "beta_async_accessor"

histogram = "histogram"
"""This StepFunc has a histogram."""

activity = "activity"
"""This StepFunc calculates the Activity."""
