"""This module implements a Neighbourhood and a StateAccessor for beta-asynchronous
step function execution.

The idea behind beta asynchronous execution is, that in a physical realisation of
a cellular automaton, there may be delays in communication between the cells
whenever the value of a neighbour is read.

This is simulated by splitting the value of a cell into an inner and an outer value.

At the beginning of each step, each cell reads its own inner value and the outer
value of each surrounding cell. These values are then used just like during normal
calculation. At the end of the step, the cell then writes the result to its inner
value and, with the probability set before, updates the outer value with the inner
value.

.. seealso::

    `zasim.cagen.nondeterministic` implements a different kind of asynchronous
    execution. While the formal definitions are compatible, the implementations
    in nondeterministic should not be mixed with the implementations in
    beta_async.


Implementation details
----------------------

This implementation realises the above specification by offering both a
`Neighbourhood` base class as well as a `StateAccessor` derived from
`SimpleStateAccessor`.

The `BetaAsynchronousNeighbourhood` acts just like `SimpleNeighbourhood`, but reads
the current outer value into orig_foo and the inner value into foo (assuming foo is
the name of the central cell.)

The `BetaAsynchronousAccessor` takes care of updating the outer state with the inner
state at the end of the computation and ensures that, in case there's any stats
object in place, at the end of the computation "foo" (as defined above) contains the
outer value of the current cell.


{LICENSE_TEXT}
"""

from .neighbourhoods import SimpleNeighbourhood
from .accessors import SimpleStateAccessor
from .utils import gen_offset_pos
from .compatibility import beta_async_neighbourhood, beta_async_accessor, random_generator

from random import Random

class BetaAsynchronousNeighbourhood(SimpleNeighbourhood):
    requires_features = [beta_async_accessor]
    provides_features = [beta_async_neighbourhood]

    def __init__(self, *args, **kwargs):
        super(BetaAsynchronousNeighbourhood, self).__init__(*args, **kwargs)
        self.center_name = [name for name, offset in zip(self.names, self.offsets)
                  if offset == (0,) or offset == (0, 0)]
        if len(self.center_name) != 1:
            raise NotImplementedError("BetaAsynchronousNeighbourhood can only"
                    " work with 1d or 2d neighbourhoods with a center.")
        else:
            self.center_name = self.center_name[0]

    def visit(self):
        """Adds C and python code to get the neighbouring values and stores
        them in local variables. The neighbouring values will be taken from the
        outer array, the own value will be taken from the inner array."""
        for name, offset in zip(self.names, self.offsets):
            if offset != (0,) and offset != (0, 0):
                self.code.add_weave_code("pre_compute", "%s = %s;" % (name,
                         self.code.acc.read_access(
                             gen_offset_pos(self.code.loop.get_pos(), offset))))
            else:
                self.code.add_weave_code("pre_compute", "orig_%s = %s;" % (name,
                         self.code.acc.read_access(
                             gen_offset_pos(self.code.loop.get_pos(), offset))))
                self.code.add_weave_code("pre_compute", "%s = %s;" % (name,
                         self.code.acc.inner_read_access(
                             self.code.loop.get_pos())))

        self.code.add_weave_code("localvars",
                "int " + ", ".join(self.names) + ";")

        assignments = ["%s = self.acc.read_from(%s)" % (
                name if offset != (0,) and offset != (0, 0) else "orig_" + name,
                "offset_pos(pos, %s)" % (offset,))
                for name, offset in zip(self.names, self.offsets)]

        if len(self.offsets[0]) == 1:
            assignments.append("%s = self.acc.read_from_inner((0,))" % self.center_name)
        else:
            assignments.append("%s = self.acc.read_from_inner((0, 0))" % self.center_name)
        self.code.add_weave_code("localvars", "int orig_" + self.center_name + ";")
        self.code.add_py_code("pre_compute",
                "\n".join(assignments))

class BetaAsynchronousAccessor(SimpleStateAccessor):
    requires_features = [beta_async_neighbourhood, random_generator]
    provides_features = [beta_async_accessor]

    def __init__(self, probab=0.5, **kwargs):
        super(BetaAsynchronousAccessor, self).__init__(**kwargs)
        self.probab = probab
        self.random = Random()

    def init_once(self):
        super(BetaAsynchronousAccessor, self).init_once()
        self.code.attrs.extend(["inner"])
        self.code.consts["beta_probab"] = self.probab

    def new_config(self):
        super(BetaAsynchronousAccessor, self).new_config()
        # XXX this function assumes, that it will be called before the
        #     border ensurer runs, so that the config is "small".
        self.target.inner = self.target.cconf.copy()

    def write_to_inner(self, pos, value):
        self.target.inner[pos] = value

    def inner_write_access(self, pos):
        return "inner(%s)" % (",".join(pos))

    def read_from_inner(self, pos):
        return self.target.inner[pos]

    def inner_read_access(self, pos):
        return self.inner_write_access(pos)

    def visit(self):
        self.code.add_weave_code("localvars",
         """int result;""")
        self.code.add_weave_code("post_compute",
                self.inner_write_access(self.code.loop.get_pos()) + " = result;")
        self.code.add_weave_code("post_compute",
                """if(rand() < RAND_MAX * beta_probab) {
                    %(write)s = result;
                } else {
                    result = %(read)s;
                    %(write)s = result;
                }
                %(center)s = orig_%(center)s;""" % \
        dict(write=self.code.acc.write_access(self.code.loop.get_pos()),
             read=self.code.acc.read_access(self.code.loop.get_pos()),
             center=self.code.neigh.center_name))

        self.code.add_py_code("init",
                """result = None""")
        for sizename, value in zip(self.size_names, self.size):
            self.code.add_py_code("init",
                    """%s = %d""" % (sizename, value))

        self.code.add_py_code("post_compute", """
            self.acc.write_to_inner(pos, result)
            if self.random.random() < beta_probab:
                self.acc.write_to(pos, result)
            else:
                result = self.acc.read_from(pos)
                self.acc.write_to(pos, result)
            %(center)s = orig_%(center)s""" % dict(center=self.code.neigh.center_name))

        self.code.add_py_code("finalize",
                """self.acc.swap_configs()""")

    def set_target(self, target):
        super(BetaAsynchronousAccessor, self).set_target(target)

    def build_name(self, parts):
        parts.insert(0, "Beta-Asynchronous (%s)" % (self.probab))

