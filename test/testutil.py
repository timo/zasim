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
            mid += "  !" + " " * (max(len(l1p), len(l2p)) - 3)

    return (equal, l1, mid, l2)

def compare_arrays(arr1, arr2):
    (equal, l1, mid, l2) = generate_pretty_printed_comparison(arr1, arr2)
    print "\n".join((l1, mid, l2))

def assert_arrays_equal(arr1, arr2):
    """assert the equality of two arrays.

    highlights different array cells if they differ.
    outputs the array if they are the same"""
    # are the arrays the same size?
    assert len(arr1) == len(arr2)

    (equal, l1, mid, l2) = generate_pretty_printed_comparison(arr1, arr2)

    if not equal:
        print l1
        print mid
        print l2
    else:
        print l1

    # are the arrays equal?
    assert equal

