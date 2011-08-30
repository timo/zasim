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
import numpy as np
from .cagen import elementary_digits_and_values

GAP = object()
"""The value passed to create_subwidget when a position is not held by a
field."""

CELL_COL = {1: "white",
            0: "black",
            GAP: "gray"}

class CellDisplayWidget(QLabel):
    def __init__(self, value, size=16, **kwargs):
        super(CellDisplayWidget, self).__init__(**kwargs)
        self.setFixedSize(size, size)
        self.setPixmap(self.__pixmap_for_value(value))

    def __pixmap_for_value(self, value):
        pixmap = QPixmap(QSize(self.width(), self.height()))
        pixmap.fill(QColor(CELL_COL[value]))
        return pixmap

class EditableCellDisplayWidget(QPushButton):
    value_changed = Signal([int])

    def __init__(self, value, base=2, size=16, **kwargs):
        super(EditableCellDisplayWidget, self).__init__(**kwargs)
        self.value = value
        self.base = base
        self.setFixedSize(size, size)
        self.setFlat(True)
        self.setAutoFillBackground(True)
        self.bg_color = QColor(CELL_COL[self.value])

        self.clicked.connect(self.change_value)

    def change_value(self):
        self.value = (self.value + 1) % self.base
        self.bg_color = QColor(CELL_COL[self.value])
        self.update()
        self.value_changed.emit(self.value)

    def paintEvent(self, event):
        paint = QPainter(self)
        paint.fillRect(event.rect(), self.bg_color)
        if self.hasFocus():
            paint.setPen(QColor("red"))
            paint.drawRect(QRect(1, 1, self.width() - 3, self.height() - 3))

class BaseNeighbourhoodDisplay(QWidget):
    """The BaseNeighbourhoodDisplay offers a skeleton for different ways of
    displaying neighbourhoods.

    Subclass this and implement create_subwidget, which will be fed an offset
    and the corresponding entry from the values dictionary, or :data:`GAP` if
    there is no spot in the neighbourhood at that position, and will then be
    put into a QGridLayout.

    This class itself displays white or black blocks in the shape of the
    neighbourhood."""

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
            subwidget = self.create_subwidget(offset, self.values.get(offset, GAP))
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
                      :data:`GAP`.
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

        self.result_widget = result_widget
        self.neighbourhood_widget = neighbourhood_widget

        if direction in "lr":
            layout = QHBoxLayout()
            spacing = self.result_widget.width()
        else:
            layout = QVBoxLayout()
            spacing = self.result_widget.height()


        if direction in "lu":
            layout.addWidget(self.result_widget)
            layout.addSpacing(spacing)
        layout.addWidget(self.neighbourhood_widget)
        if direction in "rd":
            layout.addSpacing(spacing)
            layout.addWidget(self.result_widget)

        self.setLayout(layout)

class ElementaryRuleWindow(QWidget):
    def __init__(self, neighbourhood, rule=0, base=2, **kwargs):
        super(ElementaryRuleWindow, self).__init__(**kwargs)
        self.neighbourhood = neighbourhood
        self.rule_nr = rule

        self.base = base
        self.entries = len(self.neighbourhood.offsets)

        self.rule = np.zeros(self.base ** self.entries)
        for digit in range(len(self.rule)):
            if self.rule_nr & (self.base** digit) > 0:
                self.rule[digit] = 1

        self.n_r_widgets = []
        self.display_widget = QWidget(self)
        self.display_layout = QGridLayout(self.display_widget)
        self.display_layout.setSizeConstraint(QLayout.SetFixedSize)

        digits_and_values = elementary_digits_and_values(self.neighbourhood,
                self.base, self.rule)

        for data in digits_and_values:
            data = data.copy()
            result = data["result_value"]
            del data["result_value"]
            n_w = BaseNeighbourhoodDisplay(neighbourhood, data, parent=self)
            r_w = EditableCellDisplayWidget(result, base=base, parent=self)
            n_r_w = NextToResult(n_w, r_w, parent=self, direction="r")
            self.n_r_widgets.append(n_r_w)

        self._rewrap_grid()
        self.display_widget.setLayout(self.display_layout)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidget(self.display_widget)

        layout = QHBoxLayout(self)
        layout.addWidget(self.scroll_area)
        self.setLayout(layout)

    def _rewrap_grid(self, old_width=None):
        count = len(self.n_r_widgets)
        # all items should have the same size actually
        width_per_bit = self.n_r_widgets[0].sizeHint().width() + \
                self.display_layout.spacing()
        spacing = self.display_layout.horizontalSpacing()
        if spacing == -1:
            spacing = 11

        available_width = self.contentsRect().width()
        columns = available_width / (width_per_bit) - 1

        if old_width is not None:
            old_columns = old_width / (width_per_bit) - 1
            if old_columns == columns:
                return
        if columns <= 0:
            columns = 1

        items_per_column = int(count / columns) + 1
        for widget in self.n_r_widgets:
            self.display_layout.removeWidget(widget)

        for num, widget in enumerate(self.n_r_widgets):
            col = num / items_per_column
            row = num % items_per_column
            self.display_layout.addWidget(widget, row, col)

        height_per_bit = self.n_r_widgets[0].sizeHint().height()
        v_spacing = self.display_layout.verticalSpacing()
        if v_spacing == -1:
            v_spacing = 11
        height = (height_per_bit + v_spacing) * items_per_column
        self.display_widget.setFixedSize(available_width, height)

    def resizeEvent(self, event):
        self._rewrap_grid(old_width = event.oldSize().width())

def main():
    from .cagen import VonNeumannNeighbourhood, MooreNeighbourhood
    from random import randrange
    import sys

    app = QApplication(sys.argv)

    vn = VonNeumannNeighbourhood()
    mn = MooreNeighbourhood()

    dvw = ElementaryRuleWindow(vn, rule=randrange(1024))
    dvw.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
