"""
.. testsetup:: *

    from zasim.cagen.utils import *

"""
# This file is part of zasim. zasim is licensed under the BSD 3-clause license.
# See LICENSE.txt for details.

from ..features import HAVE_TUPLE_ARRAY_INDEX

from itertools import product
import numpy as np

if HAVE_TUPLE_ARRAY_INDEX:
    def offset_pos(pos, offset):
        """Offset a position by an offset. Any amount of dimensions should work.

        >>> offset_pos((1, ), (5, ))
        (6,)
        >>> offset_pos((1, 2, 3), (9, 8, 7))
        (10, 10, 10)"""
        if len(pos) == 1:
            return (pos[0] + offset[0],)
        else:
            return tuple([a + b for a, b in zip(pos, offset)])
else:
    def offset_pos(pos, offset):
        """Offset a position by an offset. Only works for 1d."""
        if isinstance(pos, tuple):
            pos = pos[0]
        if isinstance(offset, tuple):
            offset = offset[0]
        return pos + offset

def gen_offset_pos(pos, offset):
    """Generate code to offset a position by an offset.

    >>> gen_offset_pos(["i", "j"], ["foo", "bar"])
    ['i + foo', 'j + bar']"""
    return ["%s + %s" % (a, b) for a, b in zip(pos, offset)]

def dedent_python_code(code):
    '''
    Dedent a bit of python code, like this:

    >>> print dedent_python_code("""# update the histogram
    ...     if result != center:
    ...         self.target.histogram[result] += 1""")
    # update the histogram
    if result != center:
        self.target.histogram[result] += 1
    '''

    lines = code.split("\n")
    resultlines = [lines[0]] # the first line shall never have any whitespace.
    if len(lines) > 1:
        common_whitespace = len(lines[1]) - len(lines[1].lstrip())
        if common_whitespace > 0:
            for line in lines[1:]:
                white, text = line[:common_whitespace], line[common_whitespace:]
                assert line == "" or white.isspace()
                resultlines.append(text)
        else:
            resultlines.extend(lines[1:])
    return "\n".join(resultlines)

def rule_nr_to_multidim_rule_arr(number, digits, base=2):
    """Given the rule `number`, the number of cells the neighbourhood has
    (as `digits`) and the `base` of the cells, this function calculates the
    multidimensional rule table for computing that rule."""

    if base < 256: dtype = "int8"
    else: dtype = "int16" # good luck with that.

    res = np.zeros((base,) * digits, dtype=dtype)
    entries = base ** digits
    blubb = base ** entries
    for position in product(*([xrange(base-1, -1, -1)] * digits)):
        blubb /= base
        d = int(number // (blubb))
        number -= d * (blubb)
        res[position] = d

    return res

def rule_nr_to_rule_arr(number, digits, base=2):
    """Given a rule `number`, the number of cells the neighbourhood has
    (as `digits`) and the `base` of the cells, this function calculates the
    lookup array for computing that rule.

    >>> rule_nr_to_rule_arr(110, 3)
    [0, 1, 1, 1, 0, 1, 1, 0]
    >>> rule_nr_to_rule_arr(26, 3, 3)
    [2, 2, 2, ...]
    """
    entries = base ** digits
    result = [0 for index in range(entries)]
    blubb = base ** entries
    for e in range(entries - 1, -1, -1):
        blubb /= base
        d = int(number // (blubb))
        number -= d * (blubb)
        result[e] = d

    return result

def elementary_digits_and_values(neighbourhood, base=2, rule_arr=None):
    """From a neighbourhood, the base of the values used and the array that
    holds the results for each combination of neighbourhood values, create a
    list of dictionaries with the neighbourhood values paired with their
    result_value ordered by the position like in the rule array.

    If the rule_arr is None, no result_value field will be generated."""
    digits_and_values = []
    offsets = neighbourhood.offsets
    names = neighbourhood.names
    digits = len(offsets)

    for i in range(base ** digits):
        values = rule_nr_to_rule_arr(i, digits, base)
        asdict = dict(zip(names, values))
        digits_and_values.append(asdict)

    if rule_arr is not None:
        if len(rule_arr.shape) == 1:
            indices = enumerate(xrange(base ** digits))
        else:
            indices = enumerate(product(*([xrange(base-1,-1,-1)] * digits)))

        for index, rule_idx in indices:
            digits_and_values[index].update(result_value = rule_arr[rule_idx])
    return digits_and_values

