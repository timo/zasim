import numpy as np

def compare_ndim_arrays(arr1, arr2):
    print "arr1:"
    print arr1
    print "arr2:"
    print arr2

def assert_ndim_arrays_equal(arr1, arr2):
    arr1 = arr1.flatten()
    arr2 = arr2.flatten()
    assert_arrays_equal(arr1, arr2)

def generate_pretty_printed_comparison(arr1, arr2):
    """return a pretty-printed comparison of two arrays as well as its equality:

        (equal, l1, mid, l2)"""
    equal = True
    l1, mid, l2 = "arr1 ", "     ", "arr2 "
    for i in range(len(arr1)):
        if arr1[i] != arr2[i]:
            equal = False

        l1p = " % 2d" % arr1[i]
        l2p = " % 2d" % arr2[i]
        l1 += l1p
        l2 += l2p
        if len(l1) > len(l2):
            l2 += " " * (len(l2) - len(l1))
        elif len(l1) < len(l2):
            l1 += " " * (len(l1) - len(l2))
        if arr1[i] == arr2[i]:
            mid += " " * len(l1p)
        else:
            mid += "  #" + " " * (max(len(l1p), len(l2p)) - 3)

    return (equal, l1, mid, l2)

def compare_arrays(arr1, arr2):
    if len(arr1.shape) > 1:
        compare_ndim_arrays(arr1, arr2)
        return
    (equal, l1, mid, l2) = generate_pretty_printed_comparison(arr1, arr2)
    if equal:
        print l1
    else:
        print "\n".join((l1, mid, l2))

def assert_arrays_equal(arr1, arr2):
    """assert the equality of two arrays.

    highlights different array cells if they differ.
    outputs the array if they are the same"""
    # are the arrays the same size?
    assert arr1.shape == arr2.shape

    if len(arr1.shape) > 1:
        assert_ndim_arrays_equal(arr1, arr2)
        return

    (equal, l1, mid, l2) = generate_pretty_printed_comparison(arr1, arr2)

    if not equal:
        print l1
        print mid
        print l2
    else:
        print l1

    # are the arrays equal?
    assert equal

def pretty_print_binrule(rule_arr):
    """display a key for neighbourhood to value, oriented the same way as the
    arrays are displayed"""
    l1 = []
    l2 = []
    for i in range(8):
        l1.append("%03d" % int(bin(i)[2:]))
        l2.append(str(int(rule_arr[i])))
    print " ".join(l1)
    print " " + "   ".join(l2)

INTERESTING_BINRULES = [
        26, 30, 122, 184, # triangles of different sorts
        45, 54, # other pretty rules
        110, # this one's actually able to calculate things
        ]

TESTED_BINRULE = {
        110:
           [[1,0,0,1,0,1,0,1,1,0],
            [1,0,1,1,1,1,1,1,1,0],
            [1,1,1,0,0,0,0,0,1,1],
            [1,0,1,0,0,0,0,1,1,0],
            [1,1,1,0,0,0,1,1,1,1]]}
TESTED_BINRULE = dict((k, [np.array(arr) for arr in v]) for k, v in TESTED_BINRULE.iteritems())
GLIDER = [
    [[0,1,0,0,0],
     [0,0,1,0,0],
     [1,1,1,0,0],
     [0,0,0,0,0],
     [0,0,0,0,0]],
    [[0,0,0,0,0],
     [1,0,1,0,0],
     [0,1,1,0,0],
     [0,1,0,0,0],
     [0,0,0,0,0]],
    [[0,0,0,0,0],
     [0,0,1,0,0],
     [1,0,1,0,0],
     [0,1,1,0,0],
     [0,0,0,0,0]],
    [[0,0,0,0,0],
     [0,1,0,0,0],
     [0,0,1,1,0],
     [0,1,1,0,0],
     [0,0,0,0,0]],]
try:
    GLIDER = [np.array(a) for a in GLIDER]
except:
    pass
