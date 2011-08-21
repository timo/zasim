from __future__ import absolute_import
import time
from . import ca

AVERAGE_RUNS = 2

def timedrun(fun, *args):
    st = time.time()
    try:
        fun(*args)
        et = time.time()
        return (et - st) * 1000
    except:
        raise
        return -1

def runBinRule(size, count):
    br = ca.binRule(110, size, 1, ca.binRule.INIT_RAND)
    for i in range(count):
        br.loopFunc()

def matrix(fun):
    sizes = [1000, 2000, 4000, 8000, 16000]
    counts = [1, 10000, 20000, 40000, 80000]

    timedrun(runBinRule, 1000, 1000)

    results = {}

    print " " * 10,
    for size in sizes:
        print "% 10d" % size,
    print

    for count in counts:
        print "% 10d" % count,
        for size in sizes:
            runs = [timedrun(fun, size, count) for i in range(AVERAGE_RUNS)]
            value = sum(runs) / len(runs)
            print "% 10d" % value,
            results[(count, size)] = (value, runs)
        print
    return results

allresults = {}
allresults.update(matrix(runBinRule))
print allresults
