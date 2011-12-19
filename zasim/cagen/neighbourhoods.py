"""
.. testsetup::

    from zasim.cagen import *

{LICENSE_TEXT}
"""
from .bases import Neighbourhood
from .utils import gen_offset_pos
from .compatibility import one_dimension

from itertools import product

class SimpleNeighbourhood(Neighbourhood):
    """The SimpleNeighbourhood offers named access to any number of
    neighbouring fields with any number of dimensions."""

    names = ()
    """The names of neighbourhood fields."""

    offsets = ()
    """The offsets of neighbourhood fields."""

    def __init__(self, names, offsets, name=""):
        """:param names: A list of names for the neighbouring cells.
        :param offsets: A list of offsets for each of the neighbouring cells."""
        super(Neighbourhood, self).__init__()
        self.names = tuple(names)
        self.offsets = tuple([tuple(offset) for offset in offsets])
        assert len(self.names) == len(self.offsets)
        self._sort_names_offsets()
        self.recalc_bounding_box()

        # if the neighbourhood isn't flat, make one_dimension incompatible
        if len(self.offsets[0]) == 2 and any(y != 0 for (x, y) in self.offsets):
            self.incompatible_features = [one_dimension]

        if name:
            self.neighbourhood_name = name
        else:
            try:
                self.neighbourhood_name = self.__class__.__name__
            except AttributeError:
                self.neighbourhood_name = str(self.__class__)

    def visit(self):
        """Adds C and python code to get the neighbouring values and stores
        them in local variables."""
        for name, offset in zip(self.names, self.offsets):
            self.code.add_code("pre_compute", "%s = %s;" % (name,
                     self.code.acc.read_access(
                         gen_offset_pos(self.code.loop.get_pos(), offset))))

        self.code.add_code("localvars",
                "int " + ", ".join(self.names) + ";")

        assignments = ["%s = self.acc.read_from(%s)" % (
                name, "offset_pos(pos, %s)" % (offset,))
                for name, offset in zip(self.names, self.offsets)]
        self.code.add_py_hook("pre_compute",
                "\n".join(assignments))

    def recalc_bounding_box(self):
        """Calculate a bounding box from a set of offsets."""
        # there is at least one offset and that has to have the right number of
        # dimensions already.
        num_dimensions = len(self.offsets[0])

        # initialise the maximums and minimums from the first offset
        maxes = list(self.offsets[0])
        mins = list(self.offsets[0])

        # go through all offsets
        for offset in self.offsets:
            # for each offset, go through all dimensions it has
            for dim in range(num_dimensions):
                maxes[dim] = max(maxes[dim], offset[dim])
                mins[dim] = min(mins[dim], offset[dim])

        self.bb = tuple(zip(mins, maxes))

    def bounding_box(self, steps=1):
        """Get the bounding box resulting from step successive reads.

        The return value will have an outer tuple with one tuple for
        each dimension. Each dimension will have a min and a max value.

        >>> a = SimpleNeighbourhood(list("lmr"), ((-1,), (0,), (1,)))
        >>> a.bounding_box()
        ((-1, 1),)
        >>> a.bounding_box(2)
        ((-2, 2),)
        >>> b = SimpleNeighbourhood(list("ab"), ((-5, 20), (99, 10)))
        >>> b.bounding_box()
        ((-5, 99), (10, 20))
        >>> b.bounding_box(10)
        ((-50, 990), (100, 200))
        """
        return super(SimpleNeighbourhood, self).bounding_box(steps)

    def build_name(self, parts):
        if self.neighbourhood_name:
            parts.append("with %s" % (self.neighbourhood_name))

    def affected_cells(self):
        """Get all positions of cells that have the cell at (0, 0) in their
        neighbourhood."""
        return [map(lambda x:-x, offs) for offs in self.offsets]

def ElementaryFlatNeighbourhood(Base=SimpleNeighbourhood, **kwargs):
    """This is the neighbourhood used by the elementary cellular automatons.

    The neighbours are called l, m and r for left, middle and right."""
    return Base(list("lmr"), [[-1], [0], [1]],
                "ElementaryFlatNeighbourhood", **kwargs)

def VonNeumannNeighbourhood(Base=SimpleNeighbourhood, **kwargs):
    """This is the Von Neumann Neighbourhood, in which the cell itself and the
    left, upper, lower and right neighbours are considered.

    The neighbours are called l, u, m, d and r for left, up, middle, down and
    right respectively."""
    return Base(list("uldrm"),
                [(0,-1), (-1,0), (0,1), (1,0), (0,0)],
                "VonNeumannNeighbourhood",
                **kwargs)

def MooreNeighbourhood(Base=SimpleNeighbourhood, **kwargs):
    """This is the Moore Neighbourhood. The cell and all of its 8 neighbours
    are considered for computation.

    The fields are called lu, u, ru, l, m, r, ld, d and rd for left-up, up,
    right-up, left, middle, right, left-down, down and right-down
    respectively."""

    return Base("lu u ru l m r ld d rd".split(" "),
                list(product([-1, 0, 1], [-1, 0, 1])),
                "MooreNeighbourhood",
                **kwargs)
