"""This module offers methods and user interaction widgets/windows for handling
the table-like step functions of elementary cellular automatons.

Ideas for further utilities:

 * Display conflicting rules for horizontal or vertical symmetry, rotational
   symmetry, ...
 * Make up some rules to find a "canonical" rule number for all those that just
   differ by horizontal/vertical mirroring, rotation, flipping all results, ...
 * Likewise, buttons for mirroring, rotating and flipping and otherwise
   manipulating the whole table at once.
 * An editing mode, that handles simple binary logic, like::

     c == 1 then result = 1
     c == 0 then result = 0
     l == 0 and r == 1 then result = 0

 * A graphical editing mode that allows adding "pattern matching" for rules with
   "dontcare fields" or something of that sort.
 * A graphical editing mode with zooming UI.
 * A bit of functionality to generate a rule number from arbitrary step
   functions by running them on a pre-generated target and finding out how it
   behaved.
 * ...
"""
from __future__ import absolute_import

#try:
    #from PySide.QtCore import *
    #from PySide.QtGui import *
    #print "using pyside"
#except ImportError:
    #from PyQt4.QtCore import *
    #from PyQt4.QtGui import *
    #print "using pyqt4"

from itertools import product
import numpy as np
from .cagen import elementary_digits_and_values

GAP = object()
"""The value passed to create_subwidget when a position is not held by a
field."""

CELL_COL = {1: "white",
            0: "black",
            GAP: "gray"}
"""What colors to use for what field values."""

_neighbourhood_actions = {}
def neighbourhood_action(name):
    def appender(fun):
        _neighbourhood_actions[name] = fun
        return fun
    return appender

def digits_and_values_to_rule_nr(digits_and_values, base=2):
    num = 0
    for digit, values in enumerate(digits_and_values):
        num += values["result_value"] * (base ** digit)
    return num

_minimize_cache = {}
def minimize_rule_number(neighbourhood, digits_and_values):
    original = digits_and_values_to_rule_nr(digits_and_values)
    cache = {original: ([], digits_and_values)}
    tries = [([name], digits_and_values) for name in _neighbourhood_actions]

    for route, data in tries:
        new = _neighbourhood_actions[route[-1]](neighbourhood, data)
        rule_nr = digits_and_values_to_rule_nr(new)
        if rule_nr in cache:
            oldroute, olddata = cache[rule_nr]
            if len(oldroute) > len(route):
                cache[rule_nr] = (route, new)
                tries.extend([(route + [name], new) for name in _neighbourhood_actions])
        else:
            cache[rule_nr] = (route, new)
            tries.extend([(route + [name], new) for name in _neighbourhood_actions])
    lowest_number = min(cache.keys())
    return lowest_number, cache[lowest_number], cache

#class CellDisplayWidget(QLabel):
    #"""A little Widget that displays a cell in a neighbourhood."""

    #def __init__(self, value, position=None, size=16, **kwargs):
        #"""Create the DisplayWidget.

        #:param value: The cell value to show.
        #:param position: Alternatively, the position of the cell in the result
                        #list, to be used for communication to the outside.
        #:param size: The size of the cell, used for both width and height."""
        #super(CellDisplayWidget, self).__init__(**kwargs)
        #self.setFixedSize(size, size)
        #self.setPixmap(self.__pixmap_for_value(value))
        #self.position = position

    #def __pixmap_for_value(self, value):
        #"""Create a pixmap for the value of the cell."""
        #pixmap = QPixmap(QSize(self.width(), self.height()))
        #pixmap.fill(QColor(CELL_COL[value]))
        #return pixmap

#class EditableCellDisplayWidget(QPushButton):
    #"""A clickable and keyboard-operatable display widget for cells."""

    #value_changed = Signal([int, int])
    #"""This signal will be emitted when the user changed the value of the
    #cell. It will emit the position and the new value."""

    #def __init__(self, value, position, base=2, size=16, **kwargs):
        #"""Create the editable display widget.

        #:param value: The start value.
        #:param position: The position in the result list, used in the
                         #:attr:`value_changed` signal.
        #:param base: The numerical base for values.
        #:param size: The size for the display, used for both width and height."""
        #super(EditableCellDisplayWidget, self).__init__(**kwargs)
        #self.value = value
        #self.base = base
        #self.setFixedSize(size, size)
        #self.setFlat(True)
        #self.setAutoFillBackground(True)
        #self.bg_color = QColor(CELL_COL[self.value])
        #self.position = position

        #self.clicked.connect(self._change_value)

    #def _change_value(self):
        #"""Called by the clicked signal of the underlying QPushButton."""
        #self.value = (self.value + 1) % self.base
        #self.bg_color = QColor(CELL_COL[self.value])
        #self.update()
        #self.value_changed.emit(self.position, self.value)

    #def set_value(self, value, emit=False):
        #self.value = value
        #self.bg_color = QColor(CELL_COL[self.value])
        #self.update()
        #if emit:
            #self.value_changed.emit(self.position, self.value)

    #def paintEvent(self, event):
        #"""Redraw the button, add a rectangle inside the button if it has the
        #focus."""
        #paint = QPainter(self)
        #paint.fillRect(event.rect(), self.bg_color)
        #if self.hasFocus():
            #paint.setPen(QColor("red"))
            #paint.drawRect(QRect(1, 1, self.width() - 3, self.height() - 3))

#class BaseNeighbourhoodDisplay(QWidget):
    #"""The BaseNeighbourhoodDisplay offers a skeleton for different ways of
    #displaying neighbourhoods.

    #Subclass this and implement create_subwidget, which will be fed an offset
    #and the corresponding entry from the values dictionary, or :data:`GAP` if
    #there is no spot in the neighbourhood at that position, and will then be
    #put into a QGridLayout.

    #This class itself displays white or black blocks in the shape of the
    #neighbourhood."""

    #def __init__(self, neighbourhood, values=None, **kwargs):
        #super(BaseNeighbourhoodDisplay, self).__init__(**kwargs)
        #self.neighbourhood = neighbourhood
        #self.offsets = neighbourhood.offsets
        #self.names = neighbourhood.names
        #self.bbox = self.neighbourhood.bounding_box()

        #if values is None:
            #values = dict((offs, 0) for offs in self.offsets)
        #if values.keys()[0] not in self.offsets:
            #values = dict((self.offsets[self.names.index(name)],
                           #value) for name, value in values.iteritems())
        #self.values = values.copy()

        #dims = len(self.bbox)
        #assert dims in (1, 2), "Only 1d or 2d neighbourhoods are supported"

        #if dims == 1:
            ## for making the code easier, we will only handle 2d neighbourhoods
            ## by trivially turning a 1d neighbourhood into a 2d neighbourhood.
            #self.offsets = tuple((x, 0) for x in self.offsets)
            #self.bbox = self.bbox, (0, 0)

        #self.subwidgets = {}

        #self.layout = QGridLayout(self)
        #self.layout.setContentsMargins(0, 0, 0, 0)
        #self.layout.setSpacing(0)

        #(grid_w, grid_h), (offs_x, offs_y) = self.determine_size()

        #widths  = [[] for _ in range(grid_h)]
        #heights = [[] for _ in range(grid_w)]
        #positions = product(range(grid_w),
                            #range(grid_h))
        #for (row, col) in positions:
            #offset = (row + offs_x, col + offs_y)
            #subwidget = self.create_subwidget(offset, self.values.get(offset, GAP))
            #self.subwidgets[offset] = subwidget
            #if subwidget is not None:
                #self.layout.addWidget(subwidget, row, col)
                #w, h = subwidget.width(), subwidget.height()
            #else:
                #w, h = 0, 0
            #widths[row].append(w)
            #heights[col].append(h)

        #width = max([sum(part) for part in widths])
        #height = max([sum(part) for part in heights])
        #self.setFixedSize(width, height)

    #def determine_size(self):
        #"""Determine how many fields to allocate in the grid.
        #Subclass this, if you want more gaps around the edges.

        #Return a tuple of width, height and a tuple of x-offset and y-offset."""
        #return ((self.bbox[1][1] - self.bbox[1][0] + 1,
                #self.bbox[0][1] - self.bbox[0][0] + 1),
               #(self.bbox[0][0], self.bbox[1][0]))

    #def create_subwidget(self, offset, value):
        #"""Create a widget for a cell in the neighbourhood.

        #:param offset: A tuple of (x, y) for the position of the cell
        #:param value: The value of the cell, as per the values dictionary, or
                      #if the widget is to be created for an empty space,
                      #:data:`GAP`.
        #:returns: a QWidget initialised for the cell. Alternatively, None."""
        #return CellDisplayWidget(value)

    #def update_value(self, widget, offset, new_value):
        #"""Manipulate the given widget for the new value.

        #:returns: None, if the widget was manipulated, alternatively a new
                  #QWidget to take its place."""

        #widget.setPixmap(self.__pixmap_for_value(new_value))

#class NextToResult(QWidget):
    #"""A simple utility class to display a neighbourhood widget and a result
    #widget next to each other in different relations."""
    #def __init__(self, neighbourhood_widget, result_widget, direction="l", **kwargs):
        #"""Create the widget.

        #:param neighbourhood_widget: The neighbourhood widget to put in.
        #:param result_widget: The result widget to put in.
        #:param direction: The direction the neighbourhood widget to put at.
               #Valid directions are l, u, d and r for left, up, down and right
               #respectively."""
        #super(NextToResult, self).__init__(**kwargs)
        #assert direction in "udlr"

        #self.result_widget = result_widget
        #self.neighbourhood_widget = neighbourhood_widget

        #if direction in "lr":
            #layout = QHBoxLayout()
            #spacing = self.result_widget.width()
        #else:
            #layout = QVBoxLayout()
            #spacing = self.result_widget.height()


        #if direction in "lu":
            #layout.addWidget(self.result_widget)
            #layout.addSpacing(spacing)
        #layout.addWidget(self.neighbourhood_widget)
        #if direction in "rd":
            #layout.addSpacing(spacing)
            #layout.addWidget(self.result_widget)

        #self.setLayout(layout)

#class ElementaryRuleWindow(QWidget):
    #"""A window usable to modify the table of an elementary step function."""
    #def __init__(self, neighbourhood, rule=0, base=2, **kwargs):
        #""":param neighbourhood: The :class:`Neighbourhood` instance to get the
                #data from.
           #:param rule: The rule to set at the beginning.
           #:param base: The numerical base for the cells."""
        #super(ElementaryRuleWindow, self).__init__(**kwargs)
        #self.neighbourhood = neighbourhood
        #self.rule_nr = rule

        #self.base = base
        #self.entries = len(self.neighbourhood.offsets)

        #self.rule = np.zeros(self.base ** self.entries, dtype=np.dtype("i"))
        #for digit in range(len(self.rule)):
            #if self.rule_nr & (self.base** digit) > 0:
                #self.rule[digit] = 1

        #self.n_r_widgets = []
        #self.display_widget = QWidget(self)
        #self.display_layout = QGridLayout(self.display_widget)
        #self.display_layout.setSizeConstraint(QLayout.SetFixedSize)

        #digits_and_values = elementary_digits_and_values(self.neighbourhood,
                #self.base, self.rule)

        #for pos, data in enumerate(digits_and_values):
            #data = data.copy()
            #result = data["result_value"]
            #del data["result_value"]
            #n_w = BaseNeighbourhoodDisplay(neighbourhood, data, parent=self)
            #r_w = EditableCellDisplayWidget(result, pos, base=base, parent=self)
            #n_r_w = NextToResult(n_w, r_w, parent=self, direction="r")

            #r_w.value_changed.connect(self._result_changed)

            #self.n_r_widgets.append(n_r_w)

        #self.digits_and_values = digits_and_values

        #self._rewrap_grid()
        #self.display_widget.setLayout(self.display_layout)

        #self.scroll_area = QScrollArea(self)
        #self.scroll_area.setWidget(self.display_widget)

        #layout = QVBoxLayout(self)

        #self.rule_nr_display = QLabel("Editing rule %d" % (self.rule_nr), self)
        #layout.addWidget(self.rule_nr_display)
        #layout.addWidget(self.scroll_area)

        #action_buttons = QHBoxLayout(self)
        #minimize_button = QPushButton("Minimize rule number", self)
        #minimize_button.clicked.connect(self.minimize_rule_number)
        #action_buttons.addWidget(minimize_button)

        #action_buttons.addSpacing(11)

        #for name, action in _neighbourhood_actions.iteritems():
            #act_btn = QPushButton(name, self)
            #def do_action(act=action):
                #self.do_neighbourhood_action(act)
            #act_btn.clicked.connect(do_action)
            #action_buttons.addWidget(act_btn)

        #layout.addLayout(action_buttons)

        #self.setLayout(layout)

    #def _result_changed(self, position, value):
        #"""React to a change in the results."""
        #self.digits_and_values[position]["result_value"] = value
        #self.recalculate_rule_number()

    #def recalculate_rule_number(self):
        #"""Recalculate what number corresponds to the result values saved in
        #:attr:`digits_and_values`.
        #:returns: the new rule number."""
        #num = 0
        #for digit, values in enumerate(self.digits_and_values):
            #num += values["result_value"] * (self.base ** digit)
        #self.rule_nr = num
        #self.rule_nr_display.setText("Editing rule %d" % (self.rule_nr))
        #return self.rule_nr

    #def minimize_rule_number(self):
        #best_num, (best_route, result), _ = minimize_rule_number(self.neighbourhood, self.digits_and_values)
        #if best_num == self.rule_nr:
            #QMessageBox.information(self, "No optimization found",
                    #"""This rule set is already the lowest I can make out of it.""")
        #else:
            #okay = QMessageBox.question(self, "Apply optimization?",
                    #"""With these actions, the rule number %d can be reached:
                    #%s""" % (best_num, ", ".join(best_route)),
                    #buttons=QMessageBox.Ok | QMessageBox.Cancel,
                    #defaultButton=QMessageBox.Ok)
            #if okay == QMessageBox.Ok:
                #for num, data in enumerate(result):
                    #val = data["result_value"]
                    #self.n_r_widgets[num].result_widget.set_value(val)
                #self.digits_and_values = result
                #self.recalculate_rule_number()

    #def do_neighbourhood_action(self, action):
        #print "doing", action
        #result = action(self.neighbourhood, self.digits_and_values)
        #print digits_and_values_to_rule_nr(result)
        #for num, data in enumerate(result):
            #val = data["result_value"]
            #self.n_r_widgets[num].result_widget.set_value(val)
        #self.digits_and_values = result
        #self.recalculate_rule_number()

    #def _rewrap_grid(self, old_width=None):
        #"""Put all the widgets into a grid, so that they fill just enough of
        #the width, so that there is no horizontal scroll bar."""
        #count = len(self.n_r_widgets)
        ## all items should have the same size actually
        #width_per_bit = self.n_r_widgets[0].sizeHint().width() + \
                #self.display_layout.spacing()
        #spacing = self.display_layout.horizontalSpacing()
        #if spacing == -1:
            #spacing = 11

        #available_width = self.contentsRect().width()
        #columns = available_width / (width_per_bit) - 1

        #if old_width is not None:
            #old_columns = old_width / (width_per_bit) - 1
            #if old_columns == columns:
                #return
        #if columns <= 0:
            #columns = 1

        #items_per_column = int(count / columns) + 1
        #for widget in self.n_r_widgets:
            #self.display_layout.removeWidget(widget)

        #for num, widget in enumerate(self.n_r_widgets):
            #col = num / items_per_column
            #row = num % items_per_column
            #self.display_layout.addWidget(widget, row, col)

        #height_per_bit = self.n_r_widgets[0].sizeHint().height()
        #v_spacing = self.display_layout.verticalSpacing()
        #if v_spacing == -1:
            #v_spacing = 11
        #height = (height_per_bit + v_spacing) * items_per_column
        #self.display_widget.setFixedSize(available_width, height)

    #def resizeEvent(self, event):
        #"""React to a size change of the widget."""
        #self._rewrap_grid(old_width = event.oldSize().width())

@neighbourhood_action("flip all bits")
def flip_all(neighbourhood, digits_and_values, base=2):
    ndav = []
    for data in digits_and_values:
        ndata = data.copy()
        ndata["result_value"] = base - 1 - data["result_value"]
        ndav.append(ndata)
    return ndav

def flip_values(digits_and_values, permutations=[]):
    """flip around the results, so that for each pair (a, b) the results for
    neighbourhood configurations a=a', b=b', c=c' have the values of a=b',
    b=a', c=c', for instance.

    >>> dav = [dict(l=0, r=0, result_value=1),
    ...        dict(l=0, r=1, result_value=2),
    ...        dict(l=1, r=0, result_value=3),
    ...        dict(l=1, r=1, result_value=4)]
    >>> flip_values(dav, [("l", "r")])
    [dict(l=0, r=0, result_value=1),
     dict(l=0, r=1, result_value=3),
     dict(l=1, r=0, result_value=2),
     dict(l=1, r=1, result_value=4)]
    """
    ndav = []
    def find_by_neighbours(similar):
        for num, val in enumerate(digits_and_values):
            same = True
            for k, v in similar.iteritems():
                if k == "result_value":
                    continue
                if val[k] != v:
                    same = False
                    break
            if same:
                return (num, val)
    for num, data in enumerate(digits_and_values):
        ndata = data.copy()
        for perm in permutations:
            if len(perm) == 2:
                a, b = perm
                ndata[a], ndata[b] = ndata[b], ndata[a]
            else:
                old = ndata.copy()
                for pos, npos in zip(perm, perm[1:] + [perm[0]]):
                    ndata[npos] = old[pos]
            if ndata == data:
                continue
            _, val = find_by_neighbours(ndata)
            ndata["result_value"] = val["result_value"]
        ndav.append(ndata)
    return ndav

def mirror_by_axis(neighbourhood, digits_and_values, axis=[0]):
    offs_to_name = dict(zip(neighbourhood.offsets, neighbourhood.names))
    pairs = []
    for offset, name in offs_to_name.iteritems():
        mirrored = tuple(-a if num in axis else a for num, a in enumerate(offset))
        if mirrored != offset and mirrored in offs_to_name:
            if (offs_to_name[mirrored], name) not in pairs:
                pairs.append((name, offs_to_name[mirrored]))
        elif mirrored not in offs_to_name:
            raise ValueError("Mirrored %s to %s, but could not find it in offsets!" % \
                    (offset, mirrored))

    return flip_values(digits_and_values, pairs)

@neighbourhood_action("flip vertically")
def flip_v(neighbourhood, digits_and_values):
    return mirror_by_axis(neighbourhood, digits_and_values, [1])

@neighbourhood_action("flip horizontally")
def flip_h(neighbourhood, digits_and_values):
    return mirror_by_axis(neighbourhood, digits_and_values, [0])

@neighbourhood_action("flip both")
def flip_both(neighbourhood, digits_and_values):
    return mirror_by_axis(neighbourhood, digits_and_values, [0, 1])

@neighbourhood_action("rotate clockwise")
def rotate_clockwise(neighbourhood, digits_and_values):
    def rotate(pos):
        a, b = pos
        return -b, a
    offs_to_name = dict(zip(neighbourhood.offsets, neighbourhood.names))
    print offs_to_name
    perms = []
    taken = []
    for offset, name in offs_to_name.iteritems():
        if offset in taken:
            continue
        new_offs = rotate(offset)
        perm = [offs_to_name[new_offs]]
        while new_offs != offset:
            after_rotate = rotate(new_offs)
            if after_rotate in taken:
                perm = []
                break
            taken.append(after_rotate)
            perm.append(offs_to_name[after_rotate])
            new_offs = after_rotate

        if len(perm) >= 2:
            perms.append(perm)

    print perms
    return flip_values(digits_and_values, perms)


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
