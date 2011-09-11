from ..features import HAVE_TUPLE_ARRAY_INDEX
import sys

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


CELL_SHADOW, CELL_FULL = "%#"
BACK_SHADOW, BACK_FULL = ", "
def build_array_pretty_printer(size, border, extra=((0, 0),)):
    """Generate a function that pretty-prints a configuration together with its
    border and additional fields from beyond the border.

    :attr size: A tuple describing the size of the configuration.
    :attr border: The amount of cells on each side of the configuration
                  that are beyond the border. It is formed just like the
                  output of :meth:`Neighbourhood.bounding_box`, but all values
                  have to be positive.
    :attr extra: The amount of fields to copy over in addition to the border.

    .. warning ::
        If any BorderHandler is used, that does not simply copy over fields
        from beyond the border, the output with a border or extra cells will be
        wrong!"""
    if len(extra) == 1:
        extra = (extra[0], (0, 0))
    if len(border) == 1:
        border = (border[0], (0, 0))
    def pretty_print_line(arr, sizex=size[0],
            border_left=border[0][0], border_right=border[0][1],
            extra_left=extra[0][0], extra_right=extra[0][1]):

        for cell in arr[sizex - extra_left - border_left - border_right:
                        sizex - border_right]:
            sys.stdout.write(CELL_SHADOW if cell > 0.5 else BACK_SHADOW)
        for cell in arr[border_left:sizex - border_right]:
            sys.stdout.write(CELL_FULL if cell > 0.5 else BACK_FULL)
        for cell in arr[border_left:border_left + border_right + extra_right]:
            sys.stdout.write(CELL_SHADOW if cell > 0.5 else BACK_SHADOW)
        sys.stdout.write("\n")

    if len(size) == 1:
        assert size[0] - extra[0][0] - border[0][0] - border[0][1] >= 0,\
                """Cannot put this much extra on the left"""
        assert border[0][0] + border[0][1] + extra[0][1] <= size[0],\
                """Cannot put this much extra on the left"""
        return pretty_print_line
    elif len(size) == 2:
        if extra != ((0, 0), (0, 0)):
            raise NotImplementedError("Can only pretty-print 2d without"
                                 "extra fields.")
        def pretty_print_array(arr):
            linesize = size[0]
            # draw the first and last lines as if the size were 0, but the
            # border was all of the arrays content. this way we'll get shadow
            # cells drawn above and below the arrays content.
            for y in range(0, border[1][0]):
                pretty_print_line(arr[y], linesize, linesize, 0, 0)
            for y in range(border[1][0], size[1] - border[1][1]):
                pretty_print_line(arr[y])
            for y in range(size[1] - border[1][1], size[1]):
                pretty_print_line(arr[y], linesize, linesize, 0, 0)

        return pretty_print_array
    else:
        raise NotImplementedError("Can't handle arrays of %d dimensions yet" %\
                             len(size))
