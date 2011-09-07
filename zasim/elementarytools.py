"""This module offers methods and user interaction widgets/windows for handling
the table-like step functions of elementary cellular automatons.

 * A bit of functionality to generate a rule number from arbitrary step
   functions by running them on a pre-generated target and finding out how it
   behaved.
 * ...

 .. testsetup ::

   from zasim import elementarytools

"""
from __future__ import absolute_import
from .cagen import elementary_digits_and_values, rule_nr_to_rule_arr

neighbourhood_actions = {}
def neighbourhood_action(name):
    def appender(fun):
        neighbourhood_actions[name] = fun
        return fun
    return appender

def digits_and_values_to_rule_nr(digits_and_values, base=2):
    if isinstance(digits_and_values, dict):
        digits_and_values = [val["result_value"] for val in digits_and_values]
    num = 0
    for digit, value in enumerate(digits_and_values):
        num += value * (base ** digit)
    return num

_minimize_cache = {}
def minimize_rule_number(neighbourhood, number, base=2):
    digits = base ** len(neighbourhood.offsets)
    rule_arr = rule_nr_to_rule_arr(number, digits, base)
    cache = {number: ([], rule_arr)}
    tries = [([name], rule_arr) for name in neighbourhood_actions]

    for route, data in tries:
        new = neighbourhood_actions[route[-1]](neighbourhood, data)
        rule_nr = digits_and_values_to_rule_nr(new)
        if rule_nr in cache:
            oldroute, olddata = cache[rule_nr]
            if len(oldroute) > len(route):
                cache[rule_nr] = (route, new)
                tries.extend([(route + [name], new) for name in neighbourhood_actions])
        else:
            cache[rule_nr] = (route, new)
            tries.extend([(route + [name], new) for name in neighbourhood_actions])
    lowest_number = min(cache.keys())
    return lowest_number, cache[lowest_number], cache

def minimize_rule_values(neighbourhood, digits_and_values):
    number = digits_and_values_to_rule_nr(digits_and_values)
    return minimize_rule_number(neighbourhood, number)

@neighbourhood_action("flip all bits")
def flip_all(neighbourhood, results, base=2):
    return [base - 1 - res for res in results]

def permutation_to_index_map(neighbourhood, permutation, base=2):
    """Figure out from the given neighbourhood and the permutation what
    position in the old array each entry in the new array is supposed to
    come from to realize the permutations.

    :attr neighbourhood: The neighbourhood object to use.
    :attr permutations: A dictionary that says what cell to take the value from
                        for any given cell."""

    resultless_dav = elementary_digits_and_values(neighbourhood, base)

    index_map = range(len(resultless_dav))

    for index, dav in enumerate(resultless_dav):
        ndav = dict((k, dav[permutation[k]]) for k in neighbourhood.names)

        other_index = resultless_dav.index(ndav)
        index_map[index] = other_index

    return index_map

def apply_index_map_values(digits_and_values, index_map):
    return [digits_and_values[index_map[i]] for i, _ in enumerate(digits_and_values)]

def apply_index_map(results, index_map):
    if isinstance(results, dict):
        return apply_index_map_values(results)
    return [results[index_map[i]] for i in range(len(results))]

def flip_offset_to_permutation(neighbourhood, permute_func):
    """Apply the permute_func, which takes in the offset and returns a new
    offset to the neighbourhood offsets and return a permutation dictionary
    that maps each name of a cell to the name of the cell its data is supposed
    to come from."""

    offs_to_name = dict(zip(neighbourhood.offsets, neighbourhood.names))
    permutation = dict(zip(neighbourhood.names, neighbourhood.names))
    for offset, old_name in offs_to_name.iteritems():
        new_offset = permute_func(offset)
        new_name = offs_to_name[new_offset]
        permutation[old_name] = new_name

    return permutation

def mirror_by_axis(neighbourhood, axis=[0]):
    def mirror_axis_permutation(position, axis=tuple(axis)):
        return tuple(-a if num in axis else a for num, a in enumerate(position))

    permutation = flip_offset_to_permutation(neighbourhood, mirror_axis_permutation)
    return permutation_to_index_map(neighbourhood, permutation)

@neighbourhood_action("flip vertically")
def flip_v(neighbourhood, results, cache={}):
    if neighbourhood not in cache:
        cache[neighbourhood] = mirror_by_axis(neighbourhood, [0])

    return apply_index_map(results, cache[neighbourhood])

@neighbourhood_action("flip horizontally")
def flip_h(neighbourhood, results, cache={}):
    if neighbourhood not in cache:
        cache[neighbourhood] = mirror_by_axis(neighbourhood, [1])
    return apply_index_map(results, cache[neighbourhood])

@neighbourhood_action("rotate clockwise")
def rotate_clockwise(neighbourhood, results, cache={}):
    if neighbourhood not in cache:
        def rotate((a, b)):
            return b, -a
        permutation = flip_offset_to_permutation(neighbourhood, rotate)
        cache[neighbourhood] = permutation_to_index_map(neighbourhood, permutation)

    return apply_index_map(results, cache[neighbourhood])
