from .neighbourhoods import SimpleNeighbourhood
from .accessors import SimpleStateAccessor
from .utils import gen_offset_pos

from random import Random

import numpy as np

class BetaAsynchronousNeighbourhood(SimpleNeighbourhood):
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
                self.code.add_code("pre_compute", "%s = %s;" % (name,
                         self.code.acc.read_access(
                             gen_offset_pos(self.code.loop.get_pos(), offset))))
            else:
                self.code.add_code("pre_compute", "orig_%s = %s;" % (name,
                         self.code.acc.read_access(
                             gen_offset_pos(self.code.loop.get_pos(), offset))))
                self.code.add_code("pre_compute", "%s = %s;" % (name,
                         self.code.acc.inner_read_access(
                             self.code.loop.get_pos())))

        self.code.add_code("localvars",
                "int " + ", ".join(self.names) + ";")

        assignments = ["%s = self.acc.read_from(%s)" % (
                name if offset != (0,) and offset != (0, 0) else "orig_" + name,
                "offset_pos(pos, %s)" % (offset,))
                for name, offset in zip(self.names, self.offsets)]

        if len(self.offsets[0]) == 1:
            assignments.append("%s = self.acc.read_from_inner((0,))" % self.center_name)
        else:
            assignments.append("%s = self.acc.read_from_inner((0, 0))" % self.center_name)
        self.code.add_code("localvars", "int orig_" + self.center_name + ";")
        self.code.add_py_hook("pre_compute",
                "\n".join(assignments))

class BetaAsynchronousAccessor(SimpleStateAccessor):
    def __init__(self, probab=0.5, **kwargs):
        super(BetaAsynchronousAccessor, self).__init__(**kwargs)
        self.probab = probab
        self.random = Random()

    def init_once(self):
        super(BetaAsynchronousAccessor, self).init_once()
        self.code.attrs.extend(["inner", "beta_randseed"])
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
        """Take care for result and sizeX to exist in python and C code,
        for the result to be written to the config space and for the configs
        to be swapped by the python code."""
        self.code.add_code("localvars",
         """int result;
            srand(beta_randseed(0));""")
        self.code.add_code("post_compute",
                self.inner_write_access(self.code.loop.get_pos()) + " = result;")
        self.code.add_code("post_compute",
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

        self.code.add_code("after_step",
                """beta_randseed(0) = rand();""")

        self.code.add_py_hook("init",
                """result = None""")
        for sizename, value in zip(self.size_names, self.size):
            self.code.add_py_hook("init",
                    """%s = %d""" % (sizename, value))

        self.code.add_py_hook("post_compute", """
            self.acc.write_to_inner(pos, result)
            if self.target.beta_random.random() < beta_probab:
                self.acc.write_to(pos, result)
            else:
                result = self.acc.read_from(pos)
                self.acc.write_to(pos, result)
            %(center)s = orig_%(center)s""" % dict(center=self.code.neigh.center_name))

        self.code.add_py_hook("finalize",
                """self.acc.swap_configs()""")

    def set_target(self, target):
        super(BetaAsynchronousAccessor, self).set_target(target)
        target.beta_randseed = np.array([self.random.random()])
        target.beta_random = self.random

    def build_name(self, parts):
        parts.insert(0, "Beta-Asynchronous (%s)" % (self.probab))

