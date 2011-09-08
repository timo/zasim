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

def get_swap_usage():
    with open("/proc/self/status", "r") as status:
        line = [line for line in status if line.startswith("VmSwap")][0]

    value = int(line.split()[1]) * 1024
    return value

from zasim.elementarytools import minimize_rule_number, neighbourhood_actions
from zasim import cagen

from struct import Struct
from time import time
import os

# we don't want bits to be flipped when searching for equivalent CAs.
del neighbourhood_actions["flip all bits"]

def fixed_bits(M, m):
    """Iterate over all numbers with M bits, of which m are set to 1.
    This iterates in order from smallest to biggest."""
    bit_position = list(range(m))
    num = int("1" * m, 2)
    yield num
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
        lastnum = num
        num = 0
        for pos in range(m):
            num += 2 ** bit_position[pos]

        assert lastnum < num

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

        self.taskname += "_%02d" % (self.bits_set)

        self.task_size = 0
        self._get_index_translation_table()

        self.outfile = open(self.res("output"), "w")
        self.timings = open(self.res("timings"), "w")

    def res(self, name):
        """generete a resource filename for the given name"""
        return self.taskname + "_" + name

    def _get_index_translation_table(self):
        """Trying to validate/create the index table."""
        start = time()
        struct = Struct("I")
        try:
            with open(self.res("trans_table"), "r") as table:
                table.seek(-4, os.SEEK_END)
                position = table.tell()
                self.task_size = position / 4
                result = table.read(4)
            result = struct.unpack(result)
            if result != 0:
                print "index translation table was incomplete. regenerating!"
                print "wasted %f seconds" % (time() - start)
                start = time()
                raise IOError
            print "validated index file from hard drive"
        except IOError:
            count = 0
            with open(self.res("trans_table"), "w") as table:
                for num in fixed_bits(self.digits, self.bits_set):
                    table.write(struct.pack(num))
                    count += 1
                # add a "finished" zero-fourbyte
                table.write(struct.pack(0))
            self.task_size = count
            print "wrote index translation table to file"

        print "took %f seconds for index translation table" % (time() - start)

    def loop(self):
        start = time()
        neigh = self.neigh
        stats_step = max(10, self.task_size / 2000)

        packstruct = Struct("l")

        print "writing out the size of the data dictionary every %d steps" % stats_step
        print "goint to calculate %d numbers." % (self.task_size)
        last_time = time()
        for index, number in enumerate(fixed_bits(self.digits, self.bits_set)):

            representant, (path, rule_arr), everything = minimize_rule_number(neigh, number)
            if number == representant:
                self.outfile.write(packstruct.pack(-len(everything)))
            else:
                self.outfile.write(packstruct.pack(representant))

            if index % stats_step == 0:
                endtime, last_time = time() - last_time, time()
                self.timings.write("%f %d\n" % (endtime, index))


        print "done %d steps in %s" % (self.task_size, time() - start)
        #print "representants ranged from %d to %d" % (self.low_repr, self.high_repr)
        #print "biggest group: % 2d %s" % (len(self.biggest_group), self.biggest_group)

    def cleanup(self):
        self.outfile.close()
        self.timings.close()

def new_main():
    print "let's go!"
    neigh = cagen.VonNeumannNeighbourhood()

    for bits_set in range(1, 12):
        print "starting task with %d bits set!" % (bits_set)
        a = Task(neigh, bits_set, "von_neumann")
        a.loop()
        a.cleanup()
        print

if __name__ == "__main__":
    new_main()
