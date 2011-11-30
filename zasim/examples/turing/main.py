"""This module implements a cellular automaton, that models moving data along
the tape of a turing machine."""

from zasim.display.console import MultilineOneDimConsolePainter

palette = [["a ", "a ", "a ", "a ", "b ", "b ", "b ", "b ", "c ", "c ", "c ", "c "],
           ["  ", "<a", "<b", "<c", "  ", "<a", "<b", "<c", "  ", "<a", "<b", "<c"]]
values  =  [ 0,    1,    2,    3,    4,    5,    6,    7,    8,    9,    10,   11]
palette = MultilineOneDimConsolePainter.box_art_palette(palette)
palette = MultilineOneDimConsolePainter.convert_palette(palette, values)

print palette
