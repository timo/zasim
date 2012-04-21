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
# {LICENSE_TEXT}

class CompatibilityException(Exception):
    def __init__(self, conflicts, missing):
        self.conflicts = conflicts
        self.missing = missing

    #def __repr__(self):
        #return "<CompatibilityException(conflicts=%s, missing=%s)>" % (self.conflicts, self.missing)

    def __str__(self):
        return """\
<Compatibility Exception:
    feature conflicts:
      %s

    missing features:
      %s
  >""" % ("\n      ".join(map(str, self.conflicts)),
          "\n      ".join(map(str, self.missing)))

class NoCodeGeneratedException(Exception):
    """When both the no_python_code and the no_weave_code feature are present,
    no valid code has actually been generated."""

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

no_python_code = "no_python_code"
"""This StepFunc doesn't generate pure python code."""

no_weave_code = "no_weave_code"
"""This StepFunc doesn't generate weave code."""

random_generator = "random_generator"
