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
from .cagen import elementary_digits_and_values

neighbourhood_actions = {}
def neighbourhood_action(name):
    def appender(fun):
        neighbourhood_actions[name] = fun
        return fun
    return appender

def digits_and_values_to_rule_nr(digits_and_values, base=2):
    num = 0
    for digit, values in enumerate(digits_and_values):
        num += values["result_value"] * (base ** digit)
    return num

_minimize_cache = {}
def minimize_rule_number(neighbourhood, digits_and_values):
    original = digits_and_values_to_rule_nr(digits_and_values)
    cache = {original: ([], digits_and_values)}
    tries = [([name], digits_and_values) for name in neighbourhood_actions]

    for route, data in tries:
        new = neighbourhood_actions[route[-1]](neighbourhood, data)
        rule_nr = digits_and_values_to_rule_nr(new)
        print "trying", ", ".join(route), "gives us", rule_nr
        if rule_nr in cache:
            oldroute, olddata = cache[rule_nr]
            if len(oldroute) > len(route):
                cache[rule_nr] = (route, new)
                tries.extend([(route + [name], new) for name in neighbourhood_actions])
        else:
            cache[rule_nr] = (route, new)
            tries.extend([(route + [name], new) for name in neighbourhood_actions])
    print "original number was %d" % original
    for number, (route, _) in cache.iteritems():
        print "%s leads to %d" % (", ".join(route), number)
    lowest_number = min(cache.keys())
    print "the lowest we could do was %d: %s" % (lowest_number, ", ".join(cache[lowest_number][0]))
    return lowest_number, cache[lowest_number], cache

@neighbourhood_action("flip all bits")
def flip_all(neighbourhood, digits_and_values, base=2):
    ndav = []
    for data in digits_and_values:
        ndata = data.copy()
        ndata["result_value"] = base - 1 - data["result_value"]
        ndav.append(ndata)
    return ndav

def permutations_to_index_map(neighbourhood, permutations, base=2):
    """Figure out from the given neighbourhood and the permutations what
    position in the old array each entry in the new array is supposed to
    come from to realize the permutations.

    :attr neighbourhood: The neighbourhood object to use.
    :attr permutations: A list of permutations, each of which being a 2-tuple of
                        names to exchange."""

    resultless_dav = elementary_digits_and_values(neighbourhood, base)

    index_map = range(len(resultless_dav))

    for index, dav in enumerate(resultless_dav):
        ndav = dav.copy()
        for (a, b) in permutations:
            ndav[a], ndav[b] = ndav[b], ndav[a]

        other_index = resultless_dav.index(ndav)
        index_map[index] = other_index

    return index_map

def apply_index_map(digits_and_values, index_map):
    return [digits_and_values[index_map[i]] for i, _ in enumerate(digits_and_values)]

def flip_offset_to_permutation(neighbourhood, permute_func):
    """Apply the permute_func, which takes in the offset and returns a new
    offset to the neighbourhood offsets and return pairs of (old_name,
    new_name) for each permutation operatoin."""

    offs_to_name = dict(zip(neighbourhood.offsets, neighbourhood.names))
    pairs = []
    for offset, old_name in offs_to_name.iteritems():
        new_offset = permute_func(offset)

        if new_offset != offset:
            pair = (old_name, offs_to_name[new_offset])
            pairs.append(pair)

    # it's necessary, to have no "closing pair" for each cycle, so we have to
    # organize the groups by the cycles they belong to and remove any pair from
    # every group, that joins a beginning and an end.
    # it's also necessary to sort them, so that the permutations are processed
    # in order. thus we clear the pairs array and add each link as we find it.
    cycle_groups = []
    pairs_to_consider, pairs = pairs, []
    while len(pairs_to_consider) > 0:
        changed_anything = False
        for a, b in pairs_to_consider:
            for group in cycle_groups:
                if a in group or b in group:
                    # only if this pair does not close a cycle, we add it back
                    # to the pairs array.
                    if a in group and not b in group:
                        group.extend(b)
                        pairs.append((a, b))
                        print "added %s to the cycle of %s" % ((a, b), group)
                    changed_anything = True
                    pairs_to_consider.remove((a, b))
                    break

        # if there was no result whatsoever in this round, we have to start
        # looking for a new cycle. take the first pair, which must belong to
        # any non-discovered cycle.
        if not changed_anything:
            new_pair = pairs_to_consider.pop()
            print "added %s, it starts a new cycle." % (new_pair,)
            pairs.append(new_pair)
            cycle_groups.append(list(new_pair))

    return pairs

def mirror_by_axis(neighbourhood, axis=[0]):
    def mirror_axis_permutation(position, axis=tuple(axis)):
        return tuple(-a if num in axis else a for num, a in enumerate(position))

    permutation = flip_offset_to_permutation(neighbourhood, mirror_axis_permutation)
    return permutations_to_index_map(neighbourhood, permutation)

@neighbourhood_action("flip vertically")
def flip_v(neighbourhood, digits_and_values, cache={}):
    if neighbourhood not in cache:
        cache[neighbourhood] = mirror_by_axis(neighbourhood, [0])

    return apply_index_map(digits_and_values, cache[neighbourhood])

@neighbourhood_action("flip horizontally")
def flip_h(neighbourhood, digits_and_values, cache={}):
    if neighbourhood not in cache:
        cache[neighbourhood] = mirror_by_axis(neighbourhood, [1])
    return apply_index_map(digits_and_values, cache[neighbourhood])

#@neighbourhood_action("flip both")
#def flip_both(neighbourhood, digits_and_values, cache={}):
    #if neighbourhood not in cache:
        #cache[neighbourhood] = mirror_by_axis(neighbourhood, [0, 1])
    #return flip_values(digits_and_values, cache[neighbourhood])

@neighbourhood_action("rotate clockwise")
def rotate_clockwise(neighbourhood, digits_and_values, cache={}):
    if neighbourhood not in cache:
        def rotate(pos):
            a, b = pos
            return -b, a
        permutation = flip_offset_to_permutation(neighbourhood, rotate)
        cache[neighbourhood] = permutations_to_index_map(neighbourhood, permutation)

    return apply_index_map(digits_and_values, cache[neighbourhood])
