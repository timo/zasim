from .bases import CellLoop
from .compatibility import one_dimension, two_dimensions

class OneDimCellLoop(CellLoop):
    """The OneDimCellLoop iterates over all cells in order from 0 to sizeX."""

    requires_features = [one_dimension]

    def get_pos(self):
        return "i"

    def visit(self):
        super(OneDimCellLoop, self).visit()
        self.code.add_code("loop_begin",
                """for(int i=0; i < sizeX; i++) {""")
        self.code.add_code("loop_end",
                """}""")

    def get_iter(self):
        def generator():
            for i in range(0, self.code.acc.get_size_of()):
                yield (i,)
        return iter(generator())

    def build_name(self, parts):
        parts.insert(0, "1d")

class TwoDimCellLoop(CellLoop):
    """The TwoDimCellLoop iterates over all cells from left to right, then from
    top to bottom."""

    requires_features = [two_dimensions]

    def get_pos(self):
        return "i", "j"

    def visit(self):
        super(TwoDimCellLoop, self).visit()
        size_names = self.code.acc.size_names
        self.code.add_code("loop_begin",
            """for(int i=0; i < %s; i++) {
                for(int j=0; j < %s; j++) {""" % (size_names))
        self.code.add_code("loop_end",
                """}
                }""")

    def get_iter(self):
        def iterator():
            for i in range(0, self.code.acc.get_size_of(0)):
                for j in range(0, self.code.acc.get_size_of(1)):
                    yield (i, j)
        return iter(iterator())

    def build_name(self, parts):
        parts.insert(0, "2d")

