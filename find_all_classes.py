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

from struct import Struct
from time import time
import os

from collections import defaultdict

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

        self.timings = open(self.res("timings"), "a", buffering=1)
        self.outfile = None

        self.cache = defaultdict(lambda: 0)

        cache_mb_size = 80
        cache_byte_size = cache_mb_size * 1024 * 1024
        cache_entry_size = cache_byte_size / 8
        self.cachesize = cache_entry_size

        self.items_done = 0

        self.fast_forward()

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
            result = struct.unpack(result)[0]
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

    def iter_n_bytes(self, stream, byte_c=8):
        text = stream.read(byte_c)
        while text != "":
            yield text
            text = stream.read(byte_c)

    def fast_forward(self):
        print "attempting fast_forward"
        self.number_iter = enumerate(fixed_bits(self.digits, self.bits_set))
        count = 0
        try:
            with open(self.res("output"), "r") as prev_output:
                for data in self.iter_n_bytes(prev_output):
                    index, number = self.number_iter.next()
                    count += 1

        except IOError:
            print "fast_forward encountered IOError."
        print "fast-forwarded %d entries" % count
        self.task_size -= count

    def inner_loop(self):
        if self.task_size == 0:
            print "already calculated everything."
            return

        self.outfile = open(self.res("output"), "a")
        outfile = self.outfile
        neigh = self.neigh
        stats_step = max(10, self.task_size / 2000)

        packstruct = Struct("q")

        cachesize = self.cachesize
        cachecontents = len(self.cache)

        print "writing out the size of the data dictionary every %d steps" % stats_step
        print "goint to calculate %d numbers." % (self.task_size)
        last_time = time()
        iterator = self.number_iter
        care_about_ordering = False
        for index, number in iterator:
            if self.cache[number] == 0:
                representant, (path, rule_arr), everything = minimize_rule_number(neigh, number)
                everything = everything.keys()
                everything.remove(number)
                try:
                    everything.remove(representant)
                except ValueError:
                    pass
                if len(everything) > 0:
                    lowest = everything[0] # try lowering the number of inserted high numbers
                    for num in everything:
                        if num > number and cachecontents < cachesize and (num < lowest or not care_about_ordering):
                            if self.cache[num] == 0:
                                self.cache[num] = representant
                                cachecontents += 1
                            lowest = num
                if number == representant:
                    outfile.write(packstruct.pack(-len(everything)))
                else:
                    outfile.write(packstruct.pack(representant))
            else:
                self.cachehits += 1
                if cachecontents > self.max_cache_fill:
                    self.max_cache_fill = cachecontents
                    if cachecontents > 0.75 * cachesize:
                        care_about_ordering = True
                cachecontents -= 1
                val = self.cache[number]
                del self.cache[number]
                self.outfile.write(packstruct.pack(val))

            if index % stats_step == 0:
                endtime, last_time = time() - last_time, time()
                self.timings.write("%f\n" % ((endtime * 1000) / stats_step))

            self.items_done += 1

    def loop(self):
        start = time()
        self.cachehits = 0
        self.max_cache_fill = 0
        try:
            self.inner_loop()
        finally:
            if self.outfile:
                self.outfile.close()
            if self.task_size != 0:
                print "done %d steps in %s (%d cache hits - %f%%)" % (self.items_done, time() - start, self.cachehits, 100.0 * self.cachehits / self.items_done)
                print "    that's a speed of %f steps per second" % (self.items_done / (time() - start))
                print "      cache was filled with %d at its peak" % (self.max_cache_fill)

def new_main(start, end):
    print "let's go!"
    neigh = cagen.VonNeumannNeighbourhood()

    for bits_set in range(start, end):
        print "starting task with %d bits set!" % (bits_set)
        a = Task(neigh, bits_set, "von_neumann")
        a.loop()
        print

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        start = int(sys.argv[1])
        end = int(sys.argv[2]) + 1
    else:
        start = 1
        end = 16
    new_main(start, end)
