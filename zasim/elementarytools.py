"""This module offers methods and user interaction widgets/windows for handling
the table-like step functions of elementary cellular automatons.

Ideas for further utilities:

 * Display conflicting rules for horizontal or vertical symmetry, rotational
   symmetry, ...
 * Make up some rules to find a "canonical" rule number for all those that just
   differ by horizontal/vertical mirroring, rotation, flipping all results, ...
 * Likewise, buttons for mirroring, rotating and flipping and otherwise
   manipulating the whole table at once.
 * An editing mode, that handles simple binary logic, like::

     c == 1 then result = 1
     c == 0 then result = 0
     l == 0 and r == 1 then result = 0

 * A graphical editing mode that allows adding "pattern matching" for rules with
   "dontcare fields" or something of that sort.
 * A graphical editing mode with zooming UI.
 * A bit of functionality to generate a rule number from arbitrary step
   functions by running them on a pre-generated target and finding out how it
   behaved.
 * ...

 .. testsetup ::

   from zasim import elementarytools

"""
from __future__ import absolute_import

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

def flip_values(digits_and_values, permutations=[]):
    """flip around the results, so that for each pair (a, b) the results for
    neighbourhood configurations a=a', b=b', c=c' have the values of a=b',
    b=a', c=c', for instance."""
    ndav = [a.copy() for a in digits_and_values]
    # FIXME this is utterly broken and needs a complete rewrite.
    def find_by_neighbours(similar):
        for num, val in enumerate(digits_and_values):
            same = True
            for k, v in similar.iteritems():
                if k == "result_value":
                    continue
                if val[k] != v:
                    same = False
                    break
            if same:
                return (num, val)
    for num, data in enumerate(digits_and_values):
        ndata = data.copy()
        for perm in permutations:
            if len(perm) == 2:
                a, b = perm
                ndata[a], ndata[b] = ndata[b], ndata[a]
            else:
                old = ndata.copy()
                for pos, npos in zip(perm, perm[1:] + [perm[0]]):
                    ndata[npos] = old[pos]
            if ndata == data:
                ndav.append(data)
                continue
            othernum, val = find_by_neighbours(ndata)
            ndav[othernum]["result_value"], ndav[num]["result_value"]
    return ndav

def mirror_by_axis(neighbourhood, axis=[0]):
    offs_to_name = dict(zip(neighbourhood.offsets, neighbourhood.names))
    pairs = []
    for offset, name in offs_to_name.iteritems():
        mirrored = tuple(-a if num in axis else a for num, a in enumerate(offset))
        if mirrored != offset and mirrored in offs_to_name:
            if (offs_to_name[mirrored], name) not in pairs:
                pairs.append((name, offs_to_name[mirrored]))
        elif mirrored not in offs_to_name:
            raise ValueError("Mirrored %s to %s, but could not find it in offsets!" % \
                    (offset, mirrored))

    return pairs

@neighbourhood_action("flip vertically")
def flip_v(neighbourhood, digits_and_values, cache={}):
    if neighbourhood not in cache:
        cache[neighbourhood] = mirror_by_axis(neighbourhood, [1])
    return flip_values(digits_and_values, cache[neighbourhood])

@neighbourhood_action("flip horizontally")
def flip_h(neighbourhood, digits_and_values, cache={}):
    if neighbourhood not in cache:
        cache[neighbourhood] = mirror_by_axis(neighbourhood, [0])
    return flip_values(digits_and_values, cache[neighbourhood])

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
        offs_to_name = dict(zip(neighbourhood.offsets, neighbourhood.names))
        perms = []
        taken = []
        for offset, name in offs_to_name.iteritems():
            if offset in taken:
                continue
            new_offs = rotate(offset)
            perm = [offs_to_name[new_offs]]
            while new_offs != offset:
                after_rotate = rotate(new_offs)
                if after_rotate in taken:
                    perm = []
                    break
                taken.append(after_rotate)
                perm.append(offs_to_name[after_rotate])
                new_offs = after_rotate

            if len(perm) >= 2:
                perms.append(perm)

        cache[neighbourhood] = perms

    return flip_values(digits_and_values, cache[neighbourhood])
