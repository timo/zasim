from .bases import BorderHandler
from .utils import dedent_python_code, offset_pos

from ..features import HAVE_TUPLE_ARRAY_INDEX, tuple_array_index_fixup

import numpy as np

from itertools import product, chain

class BorderSizeEnsurer(BorderHandler):
    """The BorderSizeEnsurer ensures, that - depending on the bounding box
    returned by :meth:`Neighbourhood.bounding_box` - the underlying config
    array is big enough, so that getting the neighbourhood from the outermost
    cells will not access outside the bounds of the array."""
    def new_config(self):
        """Resizes the configuration array."""
        super(BorderSizeEnsurer, self).new_config()
        bbox = self.code.neigh.bounding_box()
        borders = self.code.acc.border_size
        dims = len(bbox)
        shape = self.target.cconf.shape
        dtype = self.target.cconf.dtype
        if dims == 1:
            (left,), (right,) = self.code.acc.border_names
            new_conf = np.zeros(shape[0] + borders[left] + borders[right], dtype)
            new_conf[borders[left]:-borders[right]] = self.target.cconf
        elif dims == 2:
            # TODO figure out how to create slice objects in a general way.
            (left,up), (right,down) = self.code.acc.border_names
            new_conf = np.zeros((shape[0] + borders[left] + borders[right],
                                 shape[1] + borders[up] + borders[down]), dtype)
            new_conf[borders[left]:-borders[right],
                     borders[up]:-borders[down]] = self.target.cconf
        self.target.cconf = new_conf

    def is_position_valid(self, pos):
        # FIXME this should really use get_size_of instead of reading from size.
        for axis, size in enumerate(self.code.acc.size):
            if not (0 <= pos[axis] < size):
                return False
        return True

    def correct_position(self, pos):
        return None

class BaseBorderCopier(BorderSizeEnsurer):
    """This base class for border copiers executes a retargetted version of the
    pure-py code,that was generated for ensuring the borders are neat after a
    full step, when new_config is called.

    .. note::
        In order for this to work you have to use :meth:`tee_copy_hook` instead
        of :meth:`StepFunc.add_py_hook` for creating the border fixup
        code, so that it can be retargetted and reused."""
    def visit(self):
        """Initialise :attr:`copy_py_code`."""
        self.copy_py_code = []
        super(BaseBorderCopier, self).visit()

    def new_config(self):
        """Runs the retargetted version of the border copy code created in
        :meth:`visit`."""
        super(BaseBorderCopier, self).new_config()

        retargetted = "\n".join(self.copy_py_code)
        retargetted = retargetted.replace("self.", "self.code.")
        retargetted = retargetted.replace("write_to(", "write_to_current(")
        retargetted = retargetted.replace("read_from_next(", "read_from(")
        for dim, size_name in enumerate(self.code.acc.size_names):
            size = self.code.acc.get_size_of(dim)
            retargetted = retargetted.replace(size_name, str(size))
        for border_name, border_size in self.code.acc.border_size.iteritems():
            retargetted = retargetted.replace(border_name, str(border_size))
        if not HAVE_TUPLE_ARRAY_INDEX:
            retargetted = tuple_array_index_fixup(retargetted)

        exec retargetted in globals(), locals()

    def tee_copy_hook(self, code):
        """Append a piece of code to the "after_step" hook as well as the local
        code piece that gets retargetted and run in :meth:`new_config`."""
        self.code.add_py_hook("after_step", code)
        self.copy_py_code.append(dedent_python_code(code))

    def correct_position(self, pos):
        return tuple([pos[dim] % size
            for dim, size in enumerate(self.code.acc.size)])


class SimpleBorderCopier(BaseBorderCopier):
    """Copy over cell values, so that reading from a cell at the border over
    the border yields a sensible result.

    In the case of the SimpleBorderCopier, the borders act like "portals" to
    the opposite side of the field.

    This class should work with any number of dimensions."""
    def visit(self):
        """Generate code for copying over or otherwise handling data from the
        borders."""
        super(SimpleBorderCopier, self).visit()
        # This is the new concept for the border copier:

        # 0) (BorderSizeEnsurer) make the array big enough so that no reads will
        #    ever read outside the array
        # 1) Find out from the bounding box, what areas of the "inner" array are in
        #    need of getting data copied over.
        # 2) Iterate over all those and add all reads to out-of-array positions into
        #    a set. Name that set "outside_reads"
        # 3) Iterate over all outside_reads and figure out where they need to end up.
        #    For instance on the other side of the array, or maybe mirrored or
        #    something entirely different
        # 4) Create a dictionary copy_ops with the positions to copy to as keys and
        #    the positions to copy from as values
        # 5) Maybe/Someday, order the copy ops so that they turn into slices for
        #    numpy or so that they are especially cache efficient or anything
        # 6) Write out code to do these operations in after_step.

        bbox = self.code.neigh.bounding_box()
        dims = len(bbox)
        neighbours = self.code.neigh.offsets
        self.dimension_sizes = [self.code.acc.get_size_of(dim) for dim in range(dims)]

        slices = []
        # get only the values from the borders in a lazy manner
        #
        # this is the way it works:
        # select the dimension to consider the borders of. (dim)
        # all other dimensions will be considered fully.
        # then go through all dimensions. (subdim)
        # if subdim == dim, only put in the values at the borders
        # else, put in all values

        # TODO change this, so that it uses the accessors border_size property.
        for dim in range(dims):
            slices.append(product(*[range(0, self.dimension_sizes[sd]) if sd != dim else
                                chain(range(0, abs(bbox[dim][1])),
                                      range(self.dimension_sizes[sd] - abs(bbox[dim][0]),
                                            self.dimension_sizes[sd]))
                                for sd in range(dims)]))
        # now we have a lot of product iterators in a list. we want to chain
        # these lists together, so they form one long iterator.
        slices = chain(*slices)

        over_border= {}

        # FIXME Even though sizeX and friends are now variables in the code,
        #       the positions at the edges are still absolute, so even though
        #       sizeX is pumped into the c code from the outside, the right,
        #       lower, ... border positions still cause new C code to be
        #       compiled each time.
        #
        #       Maybe iterating "only over the relevant parts" can help this by
        #       passing the positions not as absolute values, but as relatives
        #       to the relevant sizeFoo variable.

        for pos in slices:
            for neighbour in neighbours:
                target = offset_pos(pos, neighbour)
                if isinstance(target, int): # pack this into a tuple for pypy
                    target = (target,)
                if not self.is_position_valid(target):
                    over_border[tuple(target)] = self.correct_position(target)

        copy_code = []

        for write, read in over_border.iteritems():
            copy_code.append("%s = %s;" % (
                self.code.acc.write_access(write),
                self.code.acc.write_access(read)))

            self.tee_copy_hook("""
                self.acc.write_to(%s,
                    value=self.acc.read_from_next((%s,)))""" % (write, ", ".join(map(str, read))))

        self.code.add_code("after_step",
                "\n".join(copy_code))

    def corect_position_code(self, pos):
        """Create a piece of py/c code, that calculates the source for a read
        that would set the right value at position pos, which is beyond the
        border."""
        newpos = []
        for val, size, size_name in zip(pos,
                     self.dimension_sizes, self.code.acc.size_names):
            if val < 0:
                newpos.append("%s + %s" % (size_name, val))
            elif val >= size:
                newpos.append("%s - %s" % (val, size_name))
            else:
                newpos.append("%s" % (val,))
        return tuple(newpos)


class TwoDimSlicingBorderCopier(BaseBorderCopier):
    """This class copies, with only little code, each side to the opposite
    side. It only works on two-dimensional configurations."""
    def visit(self):
        """Generate code for copying over or otherwise handling data from the
        borders."""
        super(TwoDimSlicingBorderCopier, self).visit()

        self.tee_copy_hook("""# copy the upper portion below the lower border
            for pos in product(range(0, sizeX), range(0, LOWER_BORDER)):
                self.acc.write_to((pos[0], sizeY + pos[1]),
                        self.acc.read_from_next(pos))""")

        self.tee_copy_hook("""# copy the lower portion above the upper border
            for pos in product(range(0, sizeX), range(0, UPPER_BORDER)):
                self.acc.write_to((pos[0], -pos[1] - 1),
                        self.acc.read_from_next((pos[0], sizeY - pos[1] - 1)))""")

        self.tee_copy_hook("""# copy the left portion
            # plus the upper and lower edges right of the right border
            for pos in product(range(0, RIGHT_BORDER),
                               range(-UPPER_BORDER, sizeY + LOWER_BORDER)):
                self.acc.write_to((sizeX + pos[0], pos[1]),
                        self.acc.read_from_next(pos))""")

        self.tee_copy_hook("""# copy the right portion
            # plus the upper and lower edges left of the left border
            for pos in product(range(0, LEFT_BORDER),
                               range(-UPPER_BORDER, sizeY + LOWER_BORDER)):
                self.acc.write_to((-pos[0] - 1, pos[1]),
                        self.acc.read_from_next((sizeX - pos[0] - 1, pos[1])))""")

        # and now for the fun part ...

        copy_code = []
        copy_code.append("int copy_x, copy_y;")

        # upper part to lower border
        copy_code.append("""for(copy_x = 0; copy_x < sizeX; copy_x++) {
            for(copy_y = 0; copy_y < LOWER_BORDER; copy_y++) {
                %s = %s;
            } }""" % (self.code.acc.write_access(("copy_x", "sizeY + copy_y")),
                      self.code.acc.write_access(("copy_x", "copy_y")) ))

        # lower part to upper border
        copy_code.append("""for(copy_x = 0; copy_x < sizeX; copy_x++) {
            for(copy_y = 0; copy_y < UPPER_BORDER; copy_y++) {
                %s = %s;
            } }""" % (self.code.acc.write_access(("copy_x", "-copy_y - 1")),
                      self.code.acc.write_access(("copy_x", "sizeY - copy_y - 1"))))


        # left part to right border including upper and lower edges
        copy_code.append("""for(copy_x = 0; copy_x < RIGHT_BORDER; copy_x++) {
            for(copy_y = -UPPER_BORDER; copy_y < sizeY + LOWER_BORDER; copy_y++) {
                %s = %s;
            } }""" % (self.code.acc.write_access(("sizeX + copy_x", "copy_y")),
                      self.code.acc.write_access(("copy_x", "copy_y")) ))

        # right part to left border including upper and lower edges
        copy_code.append("""for(copy_x = 0; copy_x < LEFT_BORDER; copy_x++) {
            for(copy_y = -UPPER_BORDER; copy_y < sizeY + LOWER_BORDER; copy_y++) {
                %s = %s;
            } }""" % (self.code.acc.write_access(("-copy_x - 1", "copy_y")),
                  self.code.acc.write_access(("sizeX - copy_x - 1", "copy_y"))))

        self.code.add_code("after_step",
                "\n".join(copy_code))

    def build_name(self, parts):
        parts.append("(copy borders)")

    def correct_position(self, pos):
        return (pos[0] % (self.target.size[0]),
                pos[1] % (self.target.size[1]))


class TwoDimZeroReader(BorderSizeEnsurer):
    """This BorderHandler makes sure that zeros will always be read when
    peeking over the border."""
    # there is no extra work at all to be done as compared to the
    # BorderSizeEnsurer, because it already just embeds the confs into
    # np.zero and does that for one or two dimensions.

