import numpy as np
from itertools import product

def pad_dtype(arrdtype):
    """calculates a new dtype that is padded to fit each of the dtypes cells into one integer.

    :returns: the new dtype and value ranges for the padding fields."""

    bytesize = arrdtype.itemsize

    available_bytesizes = [1, 2, 4, 8, 16, 32, 64]
    # the first higher one we can take, we do take.
    try:
        new_bytesize = [bs for bs in available_bytesizes if bs >= bytesize][0]
    except IndexError:
        raise ValueError("There is no dtype large enough to encompass one field :(")

    if new_bytesize != bytesize:
        # if the bytesizes differ, we have to pad the data up!
        pad_size = new_bytesize - bytesize

        # turn pad_size into a binary like 1101. ones tell us which sizes we need
        # for padding
        pad_binary = bin(pad_size)[2:]
        take_padders = [size + 1 for size, take in enumerate(pad_binary) if take == "1"]

        possible_value_dict = {}
        new_dtype_descrs = []
        for padval in take_padders:
            fieldname = "padding_" + str(padval)
            typename = "i" + str(padval)
            shape = ()
            new_dtype_descrs.append((fieldname, typename, shape))
            possible_value_dict[fieldname] = [0]

        new_dtype_descrs.extend(arrdtype.descr)

        new_dtype = np.dtype(new_dtype_descrs)

        return new_dtype, possible_value_dict

    return arrdtype, {}

def analyze_dtype(arrdtype, possible_value_dict):
    """generates keys for a palette from thegiven array."""

    # generate an array of all possibilities
    sizes = [len(possible_value_dict[descr[0]]) for descr in arrdtype.descr]

    all_values = np.zeros(shape=sizes, dtype=arrdtype)

    value_ranges_per_subfield = [possible_value_dict[descr[0]] for descr in arrdtype.descr]

    positions = product(*map(range, sizes))
    for position in positions:
        values = [value_ranges_per_subfield[idx][position[idx]] for idx in range(len(sizes))]
        all_values[tuple(position)] = tuple(values)

    # now change the dtype

    new_array = all_values.view()
    new_array.dtype = "i" + str(arrdtype.itemsize)

    return new_array.reshape(reduce(lambda a, b: a * b, sizes))

def pad_array_and_copy(arr):
    new_dtype, _ = pad_dtype(arr.dtype)
    if new_dtype != arr.dtype:
        # we have to copy data over because of padding
        new_arr = np.empty(arr.shape, dtype=new_dtype)
        for descr in arr.dtype.descr:
            fn = descr[0]
            # just copy all data from the fields over
            new_arr[fn] = arr[fn]
    else:
        new_arr = arr.copy()

    return new_arr

def reinterpret_as_integers(arr):
    return arr.view(dtype="i{}".format(arr.dtype.itemsize))

def uninterpret(arr, orig_dtype):
    return arr.view(dtype=orig_dtype)
