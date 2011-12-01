# -*- coding: utf8 -*-
from .bases import Computation
from .utils import elementary_digits_and_values, rule_nr_to_rule_arr

import numpy as np
from random import randrange, Random
import new

class DualRuleCellularAutomaton(Computation):
    """For two given rules and a probability, this computation executes either
    rule_a (with alpha as probability) or rule_b.

    Everything else works just like the `ElementaryCellularAutomatonBase`."""

    rule_a = 0
    """The elementary rule to use with probability `alpha`."""
    rule_b = 0
    """The elementary rule to use with probability 1 - `alpha`."""
    alpha = 0.5
    """The probability for which to use rule_a rather than rule_b."""

    digits_and_values = []
    """This list stores a list of dictionaries that for each combination of
    values for the neighbourhood cells stores the 'result_value', too.

    The result_value field is a tuple of what value to use with alpha and what
    value to use with 1-alpha probability."""

    def __init__(self, rule_a=None, rule_b=None, alpha=0.5, random_generator=None, **kwargs):
        """Create the computation.

        Supply None as either rule to get a random one."""
        super(DualRuleCellularAutomaton, self).__init__(**kwargs)
        self.rule_a = rule_a
        self.rule_b = rule_b
        self.alpha  = alpha

        if random_generator is None:
            self.random = Random()
        else:
            self.random = random_generator

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
        super(DualRuleCellularAutomaton, self).visit()

        self.neigh = zip(self.code.neigh.offsets, self.code.neigh.names)
        self.digits = len(self.neigh)

        self.base = len(self.code.possible_values)
        # the numbers in the possible values list have to start at 0 and go
        # all the way up to base-1.
        assert self.code.possible_values == tuple(range(self.base))

        if self.rule_a is None:
            self.rule_a = randrange(0, self.base ** (self.base ** self.digits))

        if self.rule_b is None:
            while self.rule_a != self.rule_b:
                self.rule_b = randrange(0, self.base ** (self.base ** self.digits))

        if self.rule_a >= self.base ** (self.base ** self.digits):
            self.rule_a = self.rule_a % (self.base ** (self.base ** self.digits))
        if self.rule_b >= self.base ** (self.base ** self.digits):
            self.rule_b = self.rule_b % (self.base ** (self.base ** self.digits))

        compute_code = ["result = 0;"]
        compute_py = ["result = 0"]
        self.code.attrs.append("rule_a")
        self.code.attrs.append("rule_b")
        self.code.attrs.append("randseed")

        self.code.add_code("localvars",
                """srand(randseed(0));""")
        self.code.add_code("after_step",
                """randseed(0) = rand();""")

        for digit_num, (offset, name) in zip(range(len(self.neigh) - 1, -1, -1), self.neigh):
            code = "result += %s * %d" % (name, self.base ** digit_num)
            compute_code.append(code + ";")
            compute_py.append(code)

        compute_code.append("""
        if(rand() < RAND_MAX * RULE_ALPHA) {
            result = rule_a(result);
        } else {
            result = rule_b(result);
        }""")

        compute_py.append("""
# choose which rule to apply
if self.random.random() < RULE_ALPHA:
    result = self.target.rule_a[int(result)]
else:
    result = self.target.rule_b[int(result)]""")

        self.code.add_code("compute", "\n".join(compute_code))
        self.code.add_py_hook("compute", "\n".join(compute_py))

    def set_target(self, target):
        """Adds the randseed attribute to the target."""
        super(DualRuleCellularAutomaton, self).set_target(target)
        # FIXME how do i get the randseed out without using np.array?
        target.randseed = np.array([self.random.random()])

    def bind(self, code):
        super(DualRuleCellularAutomaton, self).bind(code)
        code.random = self.random
        code.consts["RULE_ALPHA"] = self.alpha

    def init_once(self):
        """Generate the rule lookup array and a pretty printer."""
        super(DualRuleCellularAutomaton, self).init_once()
        entries = self.base ** self.digits
        self.target.rule_a = np.zeros(entries, np.dtype("i"))
        self.target.rule_b = np.zeros(entries, np.dtype("i"))
        rule_a = self.rule_a
        rule_b = self.rule_b

        self.target.rule_a = np.array(rule_nr_to_rule_arr(rule_a, self.digits, self.base))
        self.target.rule_b = np.array(rule_nr_to_rule_arr(rule_b, self.digits, self.base))

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

        lines[-1] = "%(result_value)s"

        template = [line[:] for line in lines]

        self.digits_and_values = \
                elementary_digits_and_values(self.code.neigh, self.base, zip(self.target.rule_a, self.target.rule_b))

        for thedict in self.digits_and_values:
            a, b = thedict["result_value"]
            if a != b:
                thedict["result_value"] = ("%s/%s" % (a, b)).center(w + 1) + " "
            else:
                thedict["result_value"] = str(a).center(w + 1) + " "

        def pretty_printer(self):
            lines = [line[:] for line in protolines]
            for thedict in self.digits_and_values:
                for line, tmpl_line in zip(lines, template):
                    line.append(tmpl_line % thedict)

            lines.append("probability: %s / %s" % (self.alpha, 1 - self.alpha))

            return "\n".join(["".join(line) for line in lines])

        self.pretty_print = new.instancemethod(pretty_printer, self, self.__class__)

    def pretty_print(self):
        """This method is generated upon init_once and pretty-prints the rules
        that this elementary cellular automaton uses for local steps."""
        return ["pretty printer is available only after the StepFunc "
                "object has been put together. also: cannot pretty-print "
                "with neighbourhoods of more than two dimensions"]

    def build_name(self, parts):
        if self.rule_a <= 255 and self.rule_b <= 255:
            mingle = str
        else:
            mingle = hex
        parts.append("calculating rule %s (%s%%) / %s" % (mingle(self.rule_a), self.alpha * 100, mingle(self.rule_b)))

