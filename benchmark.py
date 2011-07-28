import time
import CA

AVERAGE_RUNS = 2

def timedrun(fun, *args):
    st = time.time()
    try:
        fun(*args)
        et = time.time()
        return (et - st) * 1000
    except:
        return -1

def runBinRule(size, count, array):
    ca = CA.binRule(110, size, 1, CA.binRule.INIT_RAND, use_array=array)
    for i in range(count):
        ca.loopFunc()

def matrix(fun, array):
    sizes = [1000, 2000, 4000, 8000, 16000]
    counts = [1, 10000, 20000, 40000, 80000]

    timedrun(runBinRule, 1000, 1000, array)

    results = {}

    print " " * 10,
    for size in sizes:
        print "% 10d" % size,
    print

    for count in counts:
        print "% 10d" % count,
        for size in sizes:
            runs = [timedrun(fun, size, count, array) for i in range(AVERAGE_RUNS)]
            value = sum(runs) / len(runs)
            print "% 10d" % value,
            results[(array, count, size)] = (value, runs)
        print
    return results

allresults = {}
print "using numpy method"
allresults.update(matrix(runBinRule, False))
if not CA.HAVE_WEAVE:
    print "using array module:"
    allresults.update(matrix(runBinRule, True))
print allresults
