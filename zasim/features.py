"""This module probes the system for different features."""

HAVE_WEAVE = True
"""Is scipy.weave available?"""

HAVE_MULTIDIM = True
"""Is multi-dimensional numpy arrays available?"""

HAVE_TUPLE_ARRAY_INDEX = True
"""Can numpy arrays be indexed with tuples?"""

HAVE_BINCOUNT = True
"""Is numpy.bincount available?"""

def tuple_array_index_fixup(line):
    """Remove tuple-indexing operations to numpy arrays.

    .. note ::

        Only works with one-dim array access."""
    return line

try:
    import numpy as np
    np.bincount(np.array([1, 2, 3]))
except AttributeError:
    HAVE_BINCOUNT = False

try:
    from scipy import weave
    from scipy.weave import converters
except ImportError:
    HAVE_WEAVE=False

try:
    from numpy import ndarray
except:
    HAVE_MULTIDIM = False

try:
    arr = np.array(range(10))
    foo = arr[(1,)]
except TypeError:
    HAVE_TUPLE_ARRAY_INDEX = False
    import re
    TUPLE_ACCESS_FIX = re.compile(r"\((\d+),\)")
    def tuple_array_index_fixup(line):
        return TUPLE_ACCESS_FIX.sub(r"\1", line)

__all__ = ["HAVE_WEAVE", "HAVE_MULTIDIM", "HAVE_TUPLE_ARRAY_INDEX",
           "HAVE_BINCOUNT",
           "tuple_array_index_fixup"]
