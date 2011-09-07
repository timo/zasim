"""
Find all Classes
================

Given a neighbourhood and a set of "equivalency operations", this script finds
out, how many classes of really different rules there are.

Chunking up the work
====================

Since the only operation that changes the amount of bits set in the
config is the bit flip, we remove that one from the "interesting" operations.
Then, we chunk up the complete work into big chunks:

 - all 32 bit integers with 1 bit set
 - all 32 bit integers with 2 bits set
 - ...
 - all 32 bit integers with 16 bits set

:meth:`iterate_fixed_bitnum` offers an iterator over all numbers with
M bits, of which m bits are set. In the first step, it will be used to
generate a list of all numbers in the interesting chunk (or get it from
disk), as well as a translation table for later aiding in reading out the
results of the computation, that will be "compressed" into one file per
chunk."""

from zasim.elementarytools import minimize_rule_number, neighbourhood_actions
from zasim import cagen

import array
from struct import Struct
from time import time

from collections import defaultdict

# we don't want bits to be flipped when searching for equivalent CAs.
del neighbourhood_actions["flip all bits"]

def fixed_bits(M, m):
    """Iterate over all numbers with M bits, of which m are set to 1.
    This iterates in order from smallest to biggest."""
    bit_position = list(range(m))
    while bit_position[-1] != M:
        # find the lowest bit that can move up one
        for pos in range(m):
            if pos == m - 1 or bit_position[pos + 1] != bit_position[pos] + 1:
                # found a bit to move, move it.
                bit_position[pos] += 1

                # rewind all the lower bits
                bit_position[:pos] = range(pos)
                break

        if bit_position[-1] == M:
            return

        # generate the number from the bits
        num = 0
        for pos in range(m):
            num += 2 ** bit_position[pos]

        yield num

class Task(object):
    def __init__(self, neighbourhood, bits_set, taskname=None, base=2):
        """Create a task for finding all equivalency classes of the given
        neighbourhood out of all those numbers that have `bits_set` bits set."""

        self.neigh = neighbourhood
        self.base = base
        self.digits = base ** len(self.neigh.offsets)
        self.bits_set = bits_set

        if taskname is None:
            self.taskname = neighbourhood.__name__
        else:
            self.taskname = taskname

        self.taskname += "_%d" % (self.bits_set)

        self.trans_tbl = {}
        self.r_trans_tbl = []
        self._get_index_translation_table()

        self.data = defaultdict(lambda: 0)

        self.low_repr = 0
        self.high_repr = 0
        self.biggest_group = []

    def res(self, name):
        """generete a resource filename for the given name"""
        return self.taskname + "_" + name

    def _get_index_translation_table(self):
        """load from disk or create a translation table for array compression."""
        try:
            with open(self.res("trans_table"), "r") as table:
                ttable = array.array("L")
                ttable.fromstring(table.read())
            for index, number in enumerate(ttable):
                self.trans_tbl[number] = index
                self.r_trans_tbl.append(number)
            del ttable
            print "got index translation table from file"
        except IOError:
            struct = Struct("L")
            with open(self.res("trans_table"), "w") as table:
                for smallnum, num in enumerate(fixed_bits(self.digits, self.bits_set)):
                    self.trans_tbl[num] = smallnum
                    self.r_trans_tbl.append(num)
                    table.write(struct.pack(num))
            print "wrote index translation table to file"

    def set_representant(self, numbers):
        """set the representant of the given rule numbers and increment the
        number of friends the representant has.

        The representant is the lowest number of numbers."""
        increment = 0
        numbers.sort(reverse=True)
        representant = numbers.pop()
        if representant > self.high_repr:
            self.high_repr = representant
        if representant < self.low_repr:
            self.low_repr = representant
        for number in numbers:
            if self.get_data(number) != representant:
                increment += 1
                self.set_data(number, representant)
            else:
                print "tried to re-set representant of %d" % number

        repr_score = self.get_data(representant) - increment
        self.set_data(representant, repr_score)
        if abs(repr_score) > len(self.biggest_group):
            self.biggest_group = [representant] + numbers

    def get_data(self, number):
        return self.data[number]

    def set_data(self, number, data):
        self.data[number] = data

    def already_done(self, number):
        """Has the number already been assigned a representant? Or is it one?"""
        return self.get_data(number) != 0

    def loop(self):
        start = time()
        neigh = self.neigh
        for index, number in enumerate(self.r_trans_tbl[::-1]):
            if not self.already_done(number):
                representant, (path, rule_arr), everything = minimize_rule_number(neigh, number)
                self.set_representant(everything.keys())

        print "done %d steps in %s" % (len(self.r_trans_tbl), time() - start)
        print "representants ranged from %d to %d" % (self.low_repr, self.high_repr)
        print "biggest group: % 2d %s" % (len(self.biggest_group), self.biggest_group)

    def cleanup(self):
        del self.data
        del self.trans_tbl
        del self.r_trans_tbl

def new_main():
    neigh = cagen.VonNeumannNeighbourhood()

    for bits_set in range(1, 10):
        print "starting task with %d bits set!" % (bits_set)
        a = Task(neigh, bits_set, "von_neumann")
        a.loop()
        a.cleanup()
        print

if __name__ == "__main__":
    new_main()
