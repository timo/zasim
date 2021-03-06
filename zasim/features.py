"""This module probes the system for different features.


"""
# This file is part of zasim. zasim is licensed under the BSD 3-clause license.
# See LICENSE.txt for details.


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

HAVE_DTYPE_AS_INDEX = True
"""Can numpy dtypes be used as index to numpy arrays?"""

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

try:
    import numpy as np
    np.zeros((10,))[np.int8(5)]
except TypeError:
    HAVE_DTYPE_AS_INDEX = False

__all__ = ["HAVE_WEAVE", "HAVE_MULTIDIM", "HAVE_TUPLE_ARRAY_INDEX",
           "HAVE_BINCOUNT", "HAVE_DTYPE_AS_INDEX",
           "tuple_array_index_fixup"]
