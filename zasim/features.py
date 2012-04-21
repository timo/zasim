"""This module probes the system for different features.


"""
# {LICENSE_TEXT}

HAVE_WEAVE = True
"""Is scipy.weave available?"""

HAVE_MULTIDIM = True
"""Is multi-dimensional numpy arrays available?"""

HAVE_TUPLE_ARRAY_INDEX = True
"""Can numpy arrays be indexed with tuples?"""

HAVE_BINCOUNT = True
"""Is numpy.bincount available?"""

HAVE_NUMPY_RANDOM = True
"""Is numpy.random available?"""

def tuple_array_index_fixup(line):
    """Remove tuple-indexing operations to numpy arrays.

    .. note ::

        Only works with one-dim array access."""
    return line

try:
    import numpy as np
    np.bincount(np.array([1, 2, 3]))
    del np
except AttributeError:
    HAVE_BINCOUNT = False

try:
    from scipy import weave
    from scipy.weave import converters
    del weave
    del converters
except ImportError:
    HAVE_WEAVE=False

try:
    from numpy import ndarray
    del ndarray
except:
    HAVE_MULTIDIM = False

try:
    from numpy import random
    del random
except:
    HAVE_NUMPY_RANDOM = False

try:
    import numpy as np
    arr = np.array(range(10))
    foo = arr[(1,)]
    del arr
    del foo
    del np
except TypeError:
    HAVE_TUPLE_ARRAY_INDEX = False
    import re
    TUPLE_ACCESS_FIX = re.compile(r"\((\d+),\)")
    def tuple_array_index_fixup(line):
        return TUPLE_ACCESS_FIX.sub(r"\1", line)

__all__ = ["HAVE_WEAVE", "HAVE_MULTIDIM", "HAVE_TUPLE_ARRAY_INDEX",
           "HAVE_BINCOUNT",
           "tuple_array_index_fixup"]
