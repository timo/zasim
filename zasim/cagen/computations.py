# * coding: utf8
"""

"""
# This file is part of zasim. zasim is licensed under the BSD 3-clause license.
# See LICENSE.txt for details.

from __future__ import print_function

from random import randrange
from .bases import Computation
from .utils import elementary_digits_and_values, rule_nr_to_multidim_rule_arr
from .compatibility import no_weave_code, no_python_code

import new
import re
import sys

#import numpy as np

class ElementaryCellularAutomatonBase(Computation):
    """Infer a 'Gödel numbering' from the used `Neighbourhood` and
    create a computation that corresponds to the rule'th possible combination
    of values for the neighbourhood cells.

    This works with any number of dimensions."""

    rule = 0
    """The elementary cellular automaton rule to use.

    See :meth:`visit` for details on how it's used."""

    digits_and_values = []
    """This list stores a list of dictionaries that for each combination of
    values for the neighbourhood cells stores the 'result_value', too."""


    def __init__(self, rule=None, **kwargs):
        """Create the computation.

        Supply None as the rule to get a random one."""
        super(ElementaryCellularAutomatonBase, self).__init__(**kwargs)
        self.rule = rule

    def visit(self):
        """Get the rule'th cellular automaton for the given neighbourhood.

        First, find out, how many possible combinations there are.
        That's simply the nuber of cells in the neighbourhood as the exponent
        of the number of `possible_values`.
        Then, normalise the neighbourhood cells by sorting their positions
        first by X, then by Y axis.
        Finally, create code, that sums up all the values and looks up the
        target value from the rule lookup array.
        """
        super(ElementaryCellularAutomatonBase, self).visit()

        self.neigh = zip(self.code.neigh.offsets, self.code.neigh.names)
        self.digits = len(self.neigh)

        self.base = len(self.code.possible_values)
        # the numbers in the possible values list have to start at 0 and go
        # all the way up to base-1.
        assert self.code.possible_values == tuple(range(self.base))

        if self.rule is None:
            self.rule = randrange(0, self.base ** (self.base ** self.digits))

        if self.rule >= self.base ** (self.base ** self.digits):
            self.rule = self.rule % (self.base ** (self.base ** self.digits))

        compute_code = []
        compute_py = []
        self.code.attrs.append("rule")

        access_pos = ", ".join(self.code.neigh.names)

        compute_code.append("result = rule(%s);" % access_pos)
        compute_py.append("result = self.target.rule[%s]" % access_pos)

        self.code.add_weave_code("compute", "\n".join(compute_code))
        self.code.add_py_code("compute", "\n".join(compute_py))

    def init_once(self):
        """Generate the rule lookup array and a pretty printer."""
        super(ElementaryCellularAutomatonBase, self).init_once()
        rule = self.rule

        self.target.rule = rule_nr_to_multidim_rule_arr(rule, self.digits, self.base)

        # and now do some heavy work to generate a pretty-printer!
        bbox = self.code.neigh.bounding_box()
        offsets = self.code.neigh.offsets
        offset_to_name = dict(self.neigh)

        if len(bbox) == 1:
            h = 3
            y_offset = None
        elif len(bbox) == 2:
            h = bbox[1][1] - bbox[1][0] + 3
            y_offset = bbox[1][0]
        else:
            # for higher dimensions, just fall back to the dummy pretty-printer
            return
        protolines = [[] for i in range(h)]
        lines = [line[:] for line in protolines]
        w = bbox[0][1] + 1 - bbox[0][0]

        for y in range(h):
            for x in range(bbox[0][0], bbox[0][1] + 1):
                if h == 3 and (x,) in offsets and y == 0:
                    lines[y].append("%(" + offset_to_name[(x,)]
                               + ")d")
                elif h > 3 and (x, y + y_offset) in offsets:
                    lines[y].append("%(" + offset_to_name[(x, y + y_offset)]
                               + ")d")
                else:
                    lines[y].append(" ")
            lines[y] = "".join(lines[y]) + "  "

        lines[-1] = ("X".center(w) + "  ").replace("X", "%(result_value)d")

        template = [line[:] for line in lines]

        self.digits_and_values = \
                elementary_digits_and_values(self.code.neigh, self.base, self.target.rule)

        def pretty_printer(self):
            lines = [line[:] for line in protolines]
            for thedict in self.digits_and_values:
                for line, tmpl_line in zip(lines, template):
                    line.append(tmpl_line % thedict)

            return "\n".join(["".join(line) for line in lines])

        self.pretty_print = new.instancemethod(pretty_printer, self, self.__class__)

    def pretty_print(self):
        """This method is generated upon init_once and pretty-prints the rules
        that this elementary cellular automaton uses for local steps."""
        return ["pretty printer is available only after the StepFunc "
                "object has been put together. also: cannot pretty-print "
                "with neighbourhoods of more than two dimensions"]

    def build_name(self, parts):
        if self.rule <= 255:
            mingle = str
        elif self.rule > 0xffffff:
            def mingle(value):
                raw = hex(value)
                chunks, raw = [raw[0:6]], raw[6:]
                for idx in range(len(raw)/4):
                    chunks.append(raw[idx * 4:idx * 4 + 4])
                return " ".join(chunks)
        else:
            mingle = hex
        parts.append("calculating rule %s" % (mingle(self.rule)))

class CountBasedComputationBase(Computation):
    """This base class counts the amount of nonzero neighbours excluding the
    center cell and offers the result as a local variable called
    nonzerocount of type int.

    The name of the central neighbour will be provided as self.central_name.
    """

    def visit(self):
        """Generate code that calculates nonzerocount from all neighbourhood
        values."""
        super(CountBasedComputationBase, self).visit()
        names = list(self.code.neigh.names)
        offsets = self.code.neigh.offsets

        # kick out the center cell, if any.
        zero_offset = tuple([0] * len(offsets[0]))
        zero_position = offsets.index(zero_offset)
        if zero_position != -1:
            self.central_name = names.pop(zero_position)
        else:
            self.central_name = None

        self.code.add_weave_code("localvars", "int nonzerocount;")
        if self.code.possible_values == (0, 1):
            single_values = names
        else:
            single_values = ["int(%d != 0)" % name for name in names]
        code = "nonzerocount = %s" % (" + ".join(single_values))

        self.code.add_weave_code("compute", code + ";")
        self.code.add_py_code("compute", code)

class LifeCellularAutomatonBase(CountBasedComputationBase):
    """This computation base is useful for any game-of-life-like step function
    in which the number of ones in the neighbourhood of a cell are counted to
    decide wether to change a 0 into a 1 or the other way around."""

    def __init__(self, reproduce_min=3, reproduce_max=3,
                 stay_alive_min=2, stay_alive_max=3, **kwargs):
        """:param reproduce_min: The minimal number of alive cells needed to
                                 reproduce to this cell.
           :param reproduce_max: The maximal number of alive cells that still
                                 cause a reproduction.
           :param stay_alive_min: The minimal number of alive neighbours needed
                                  for a cell to survive.
           :param stay_alive_max: The maximal number of alive neighbours that
                                  still allow the cell to survive."""
        super(LifeCellularAutomatonBase, self).__init__(**kwargs)
        self.params = dict(reproduce_min = reproduce_min,
                reproduce_max = reproduce_max,
                stay_alive_min = stay_alive_min,
                stay_alive_max = stay_alive_max)

    def visit(self):
        """Generates the code that turns a 0 into a 1 if nonzerocount exceeds
        reproduce_min and doesn't exceed reproduce_max and turns a 1 into a 0
        if nonzerocount is lower than stay_alive_min or higher than
        stay_alive_max."""
        super(LifeCellularAutomatonBase, self).visit()
        assert self.central_name is not None, "Need a neighbourhood with a named zero offset"
        self.params.update(central_name=self.central_name)
        self.code.add_weave_code("compute",
                """
    result = %(central_name)s;
    if (%(central_name)s == 0) {
      if (nonzerocount >= %(reproduce_min)d && nonzerocount <= %(reproduce_max)d) {
        result = 1;
    }} else {
      if (nonzerocount < %(stay_alive_min)d || nonzerocount > %(stay_alive_max)d) {
        result = 0;
      }}""" % self.params)
        self.code.add_py_code("compute","""
            result = %(central_name)s
            if %(central_name)s == 0:
                if %(reproduce_min)d <= nonzerocount <= %(reproduce_max)d:
                  result = 1
            else:
                if not (%(stay_alive_min)d <= nonzerocount <= %(stay_alive_max)d):
                  result = 0""" % self.params)

    def build_name(self, parts):
        if self.params != dict(reproduce_min=3, reproduce_max=3,
                stay_alive_min=2, stay_alive_max=3, central_name=self.params["central_name"]):
            parts.append("calculating life - reproduce "\
                    "[%(reproduce_min)s:%(reproduce_max)s], "\
                    "stay alive [%(stay_alive_min)s: %(stay_alive_max)s]" % self.params)
        else:
            parts.append("calculating game of life")

# our subcell syntax looks like this: "SubCell@Neighbour", "SubCell@NeighboursNeighbour@Neighbour", ...
subcell_syntax = re.compile(r"""
    (?P<all>                   # if cell and neighbour are not in our dictionaries,
                               # we have to return the string untouched
                               # (although: what does a @ do in python/C code?)
    (?P<cell>[a-zA-Z_]+)       # start with a subcell name
    \@                         # match a verbatim @
    (?P<neighbour>
        [a-zA-Z_]+             # neighbour names are just like cell names.
    ))""", re.X)
def fixup_subcell_syntax(code, neighbours, subcells, language="py"):
    assert language == "py"
    def replacer(match):
        print(match.groupdict())
        print(subcells, " <- cells")
        print(neighbours, " <- neighbours")
        if match.group("cell") in subcells:
            if match.group("neighbour") in neighbours or match.group("neighbour") == "result":
                return "{neighbour}_{cell}".format(**match.groupdict())
            else:
                print("warning: refered to to unknown neighbour {neighbour}".format(**match.groupdict()), file=sys.stderr)
        else:
            print("warning: refered to to unknown subcell {cell}".format(**match.groupdict()), file=sys.stderr)

        return match.group("all")
    return subcell_syntax.sub(replacer, code)

class PasteComputation(Computation):
    def __init__(self, c_code=None, py_code=None, name=None):
        if c_code is None:
            self.provides_features.append(no_weave_code)
        self.c_code = c_code
        if py_code is None:
            self.provides_features.append(no_python_code)
        self.py_code = py_code

    def visit(self):
        if self.py_code is not None:
            subcells = None
            try:
                subcells = self.code.acc.cells
            except AttributeError: pass
            neighbours = self.code.neigh.names
            if subcells:
                print(subcells)
                self.py_code = fixup_subcell_syntax(self.py_code, neighbours, subcells)
            self.code.add_py_code("compute", self.py_code)
        if self.c_code is not None:
            self.code.add_weave_code("compute", self.c_code)
