from zasim.elementarytools import minimize_rule_number
from zasim.cagen import VonNeumannNeighbourhood, elementary_digits_and_values
import numpy as np
from time import time
import os

neigh = VonNeumannNeighbourhood()
rule = np.zeros(2 ** 5, dtype=np.dtype("i"))
known = set()
counter = 0
cache_hits = 0
last_tick = 0
start_num = 2 ** 32
try:
    with open("smaller_results.txt", "r") as old_results:
        old_results.seek(-200, os.SEEK_END)
        lastline = old_results.readlines()[-1].strip()
        numbers = lastline.split(" < ")
        numbers = map(int, numbers)
        start_num = max(numbers)
except IOError:
    pass

last_bunch = time()
last_num = start_num

print "resuming from %d" % (start_num)

def prune_high_numbers_from_cache(begin, end):
    global known
    prune_begin = time()
    known = known.difference(set(range(begin, end)))
    print "prune took %s seconds" % (time() - prune_begin)

try:
    with open("smaller_results.txt", "a") as results:
        with open("smaller_timings.txt", "a") as timings:
            timings.write("started a new session from %d at %s\n" % (start_num, time()))
            for rule_nr in range(start_num, 0, -1):
                startt = time()
                if rule_nr in known:
                    cache_hits += 1
                    continue
                for digit in range(len(rule)):
                    if rule_nr & (2 ** digit) > 0:
                        rule[digit] = 1
                    else:
                        rule[digit] = 0
                dav = elementary_digits_and_values(neigh, 2, rule)
                lower, (route, _), cache = minimize_rule_number(neigh, dav)
                if lower < rule_nr:
                    nom = [lower] + cache.keys()
                    known = known.union(set([lower] + cache.keys()).difference([rule_nr]))
                    results.write(" < ".join(str(num) for num in nom))
                    results.write("\n")
                    counter += len(nom)
                if counter > last_tick + 100000:
                    timings.write("%d of %d at %s\n" % (counter, rule_nr, time()))
                    print "%d counts took %s seconds - %d cache hits so far" % (counter - last_tick, time() - last_bunch, cache_hits)
                    last_bunch = time()
                    results.flush()
                    timings.flush()
                    last_tick = counter
                    prune_high_numbers_from_cache(rule_nr, last_num)
                    last_num = rule_nr
                took = time() - startt
                if took > 1:
                    # if we're getting real slow, flush the known cache.
                    print "flushing known cache."
                    print "size was %d entries" % known
                    print "cache hit count was %d" % cache_hits
                    known = set()
finally:
    print "end-of-run stats:"
    print "cache size was %d - was hit %d times" % (len(known), cache_hits)
    print "started out at %d, went down to %d" % (start_num, rule_nr)
    print "last bunch took %s and covered %d numbers" % (time() - last_bunch, counter - last_tick)
