from __future__ import absolute_import

try:
    from PySide.QtCore import *
    from PySide.QtGui import *
    print "using pyside"
except ImportError:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    print "using pyqt4"

from itertools import product

class BaseNeighbourhoodDisplay(QWidget):
    """The BaseNeighbourhoodDisplay offers a skeleton for different ways of
    displaying neighbourhoods.

    Subclass this and implement create_subwidget, which will be fed an offset
    and the corresponding entry from the values dictionary and will then be
    put into a QGridLayout.

    This class itself displays white or black blocks in the shape of the
    neighbourhood."""

    gap = object()
    """The value passed to create_subwidget when a position is not held by a
    field."""

    def __init__(self, neighbourhood, values=None, **kwargs):
        super(BaseNeighbourhoodDisplay, self).__init__(**kwargs)
        self.neighbourhood = neighbourhood
        self.offsets = neighbourhood.offsets
        self.names = neighbourhood.names
        self.bbox = self.neighbourhood.bounding_box()

        if values is None:
            values = dict((offs, 0) for offs in self.offsets)
        if values.keys()[0] not in self.offsets:
            values = dict((self.offsets[self.names.index(name)],
                           value) for name, value in values.iteritems())
        self.values = values.copy()

        dims = len(self.bbox)
        assert dims in (1, 2), "Only 1d or 2d neighbourhoods are supported"

        if dims == 1:
            # for making the code easier, we will only handle 2d neighbourhoods
            # by trivially turning a 1d neighbourhood into a 2d neighbourhood.
            self.offsets = tuple((x, 0) for x in self.offsets)
            self.bbox = self.bbox, (0, 0)

        self.subwidgets = {}

        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        print self.bbox[1][1] - self.bbox[1][0]
        widths  = [[] for _ in range(self.bbox[1][1] - self.bbox[1][0]+1)]
        heights = [[] for _ in range(self.bbox[0][1] - self.bbox[0][0]+1)]
        print widths
        print heights
        positions = product(range(self.bbox[0][0], self.bbox[0][1]+1),
                            range(self.bbox[1][0], self.bbox[1][1]+1))
        for offset in positions:
            subwidget = self.create_subwidget(offset, self.values.get(offset, self.gap))
            self.subwidgets[offset] = subwidget
            row, col = offset
            row -= self.bbox[0][0]
            col -= self.bbox[1][0]
            if subwidget is not None:
                self.layout.addWidget(subwidget, row, col)
                w, h = subwidget.width(), subwidget.height()
            else:
                w, h = 0, 0
            print row, col
            widths[row].append(w)
            heights[col].append(h)

        width = max([sum(part) for part in widths])
        height = max([sum(part) for part in heights])
        self.setFixedSize(width, height)

    def create_subwidget(self, offset, value):
        if value == self.gap:
            return
        subwidget = QLabel(self)
        pixmap = QPixmap(QSize(32, 32))
        pixmap.fill(QColor("white" if value == 1 else "black"))
        subwidget.setPixmap(pixmap)
        subwidget.setFixedSize(32, 32)
        return subwidget

class ElementaryRuleWindow(QWidget):
    def __init__(self, neighbourhood, rule=0):
        self.neighbourhood = neighbourhood
        self.rule = rule


def main():
    from .cagen import VonNeumannNeighbourhood, MooreNeighbourhood
    from random import choice
    import sys

    app = QApplication(sys.argv)

    vn = VonNeumannNeighbourhood()
    mn = MooreNeighbourhood()

    from pudb import set_trace; set_trace()

    dvn = BaseNeighbourhoodDisplay(vn, dict((n, choice([0, 1])) for n
                                   in vn.names))
    dvn.show()
    dmn = BaseNeighbourhoodDisplay(mn, dict((n, choice([0, 1])) for n
                                   in mn.names))
    dmn.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
