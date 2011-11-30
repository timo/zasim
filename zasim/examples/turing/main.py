"""This module implements a cellular automaton, that models moving data along
the tape of a turing machine."""

from zasim.display.console import MultilineOneDimConsolePainter
from zasim.simulator import BaseSimulator, TargetProxy
from zasim.config import RandomInitialConfiguration

palette = [[" a", " a", " a", " a", " b", " b", " b", " b", " c", " c", " c", " c"],
           ["<a", "<b", "<c", "  ", "<a", "<b", "<c", "  ", "<a", "<b", "<c", "  "]]
values  =  [ 0,    1,    2,    3,    4,    5,    6,    7,    8,    9,    10,   11]
probabs =  [0.1,   0,    0,   0.23,  0,  0.1,    0,   0.23,  0,    0,    0.1, 0.24]
palette = MultilineOneDimConsolePainter.box_art_palette(palette)
palette = MultilineOneDimConsolePainter.convert_palette(palette, values)

class TuringTapeSimulator(BaseSimulator):
    def __init__(self):
        super(TuringTapeSimulator, self).__init__()

        self.shape = (25,)
        self.cconf = RandomInitialConfiguration(12, *probabs).generate((self.shape))
        # do not send stuff from the right border.
        self.cconf[-1] = self.cconf[-1] | 3

        self.possible_values = values

        self.target_attrs = ["cconf", "possible_values"]

        self.t = TargetProxy(self, self.target_attrs)


    def get_config(self):
        return self.cconf

    def step(self):
        for index, (cell, next_cell) in enumerate(zip(self.cconf[:-1], self.cconf[1:])):
            result = cell
            if next_cell & 3 == 3:
                # if the lowest 2 bytes are 1, no information is transferred and
                # the transferal state is cleared
                result = cell | 3
            else:
                # otherwise, the information from the right is moved here
                # and the own information is transferred.
                result = (next_cell & 3) << 2 | (cell & ~3) >> 2

            self.cconf[index] = result

        self.step_number += 1
        self.updated.emit()

tape = TuringTapeSimulator()
painter = MultilineOneDimConsolePainter(tape, palette, compact_boxes=True)

painter.after_step()
print

for i in range(10):
    tape.step()
    print

