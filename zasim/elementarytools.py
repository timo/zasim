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

class CellDisplayWidget(QLabel):
    def __init__(self, value, size=32, **kwargs):
        super(CellDisplayWidget, self).__init__(**kwargs)
        self.setFixedSize(size, size)
        self.setPixmap(self.__pixmap_for_value(value))

    def __pixmap_for_value(self, value):
        pixmap = QPixmap(QSize(self.width(), self.height()))
        color = {1: "white",
                 0: "black",
                 self.gap: "gray"}
        pixmap.fill(QColor(color[value]))
        return pixmap

class BaseNeighbourhoodDisplay(QWidget):
    """The BaseNeighbourhoodDisplay offers a skeleton for different ways of
    displaying neighbourhoods.

    Subclass this and implement create_subwidget, which will be fed an offset
    and the corresponding entry from the values dictionary, or :attr:`gap` if
    there is no spot in the neighbourhood at that position, and will then be
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

        (grid_w, grid_h), (offs_x, offs_y) = self.determine_size()

        widths  = [[] for _ in range(grid_h)]
        heights = [[] for _ in range(grid_w)]
        positions = product(range(grid_w),
                            range(grid_h))
        for (row, col) in positions:
            offset = (row + offs_x, col + offs_y)
            subwidget = self.create_subwidget(offset, self.values.get(offset, self.gap))
            self.subwidgets[offset] = subwidget
            if subwidget is not None:
                self.layout.addWidget(subwidget, row, col)
                w, h = subwidget.width(), subwidget.height()
            else:
                w, h = 0, 0
            widths[row].append(w)
            heights[col].append(h)

        width = max([sum(part) for part in widths])
        height = max([sum(part) for part in heights])
        self.setFixedSize(width, height)

    def determine_size(self):
        """Determine how many fields to allocate in the grid.
        Subclass this, if you want more gaps around the edges.

        Return a tuple of width, height and a tuple of x-offset and y-offset."""
        return ((self.bbox[1][1] - self.bbox[1][0] + 1,
                self.bbox[0][1] - self.bbox[0][0] + 1),
               (self.bbox[0][0], self.bbox[1][0]))

    def create_subwidget(self, offset, value):
        """Create a widget for a cell in the neighbourhood.

        :param offset: A tuple of (x, y) for the position of the cell
        :param value: The value of the cell, as per the values dictionary, or
                      if the widget is to be created for an empty space,
                      :attr:`self.gap`.
        :returns: a QWidget initialised for the cell. Alternatively, None."""
        return CellDisplayWidget(value)

    def update_value(self, widget, offset, new_value):
        """Manipulate the given widget for the new value.

        :returns: None, if the widget was manipulated, alternatively a new
                  QWidget to take its place."""

        widget.setPixmap(self.__pixmap_for_value(new_value))

class NextToResult(QWidget):
    def __init__(self, neighbourhood_widget, result_widget, direction="l", **kwargs):
        super(NextToResult, self).__init__(**kwargs)
        assert direction in "udlr"
        if direction in "lr":
            layout = QHBoxWidget()
        else:
            layout = QVBoxWidget()

        self.result_widget = result_widget
        self.neighbourhood_widget = neighbourhood_widget

        if direction in "lu":
            layout.addWidget(self.result_widget)
        layout.addWidget(self.neighbourhood_widget)
        if direction in "rd":
            layout.addWidget(self.result_widget)

        self.setLayout(layout)

class ElementaryRuleWindow(QWidget):
    def __init__(self, neighbourhood, rule=0):
        self.neighbourhood = neighbourhood
        self.rule = rule

        self.n_r_widgets = []
        layout = QHBoxLayout()

        for data in self.neighbourhood.digits_and_values:
            data = data.copy()
            result = data["result"]
            del data["result"]
            n_w = BaseNeighbourhoodDisplay(neighbourhood, data, parent=self)
            r_w = CellDisplayWidget(result, parent=self)
            n_r_w = NextToResult(n_w, r_w, parent=self)
            self.n_r_widgets.append(n_r_w)
            layout.addWidget(n_r_w)

        self.setLayout(layout)

def main():
    from .cagen import VonNeumannNeighbourhood, MooreNeighbourhood
    from random import choice
    import sys

    app = QApplication(sys.argv)

    vn = VonNeumannNeighbourhood()
    mn = MooreNeighbourhood()

    from pudb import set_trace; set_trace()

    dvw = ElementaryRuleWindow(vn)
    dvw.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
