"""
.. testsetup:: *

    from zasim.cagen.utils import *

"""
from ..features import HAVE_TUPLE_ARRAY_INDEX

if HAVE_TUPLE_ARRAY_INDEX:
    def offset_pos(pos, offset):
        """Offset a position by an offset. Any amount of dimensions should work.

        >>> offset_pos((1, ), (5, ))
        (6,)
        >>> offset_pos((1, 2, 3), (9, 8, 7))
        (10, 10, 10)"""
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
    for e in range(entries - 1, -1, -1):
        d = int(number // (base ** e))
        number -= d * (base ** e)
        result[e] = d

    return result

def elementary_digits_and_values(neighbourhood, base, rule_arr=None):
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
        values = [1 if (i & (base ** k)) > 0 else 0
                for k in range(len(offsets))]
        asdict = dict(zip(names, values))
        digits_and_values.append(asdict)

    if rule_arr is not None:
        for index in range(base ** digits):
            digits_and_values[index].update(result_value = rule_arr[index])
    return digits_and_values

