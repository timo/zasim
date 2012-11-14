# -*- coding: utf8 -*-
# vi: foldmethod=marker
from zasim.cagen import *
from zasim.cagen.signal import SignalService
from zasim.external.qt import QPixmap, QPainter, QRect, QSize, QPoint
import random

import numpy as np

# those are the offsets to be used by our neighbourhood and
# referenced in several other places.
von_neumann_offsets = [(-1,0), (0,-1), (0,0), (0,1), (1,0)]

class Tape(StepFuncVisitor):
    """The Tape class offers a list that can be read from and written
    to, much like the one found in a Turing Machine."""
    # TODO this needs functions like peek, read+advance, write+advance, rewind
    def __init__(self, content):
        self.initial_content = list(content)

    def visit(self):
        self.code.attrs.append("tape")

    def set_target(self, target):
        super(Tape, self).set_target(target)
        self.target.tape = self.initial_content.copy()

class HasOrigin(StepFuncVisitor):
    """This class offers a constant 'origin_pos' and a boolean flag 'is_origin'
    for automatons where one cell is identified as 'the origin'"""
    # TODO include a is_origin flag in the local variables
    def __init__(self, origin_pos):
        self.origin_pos = origin_pos

    def visit(self):
        self.code.attrs.append("origin_pos")

    def set_target(self, target):
        super(HasOrigin, self).set_target(target)
        self.target.origin_pos = self.origin_pos.copy()

def render_state_array_multi_tiled(statedict, palettizer, palette, rects, opainter=None):
    """This function renders a configuration using a palettizer function, that
    can render multiple transparent images in the same cell to make composite
    cell graphics.
    
    The palettizer function gets the configuration and current position
    and returns a list of (destination_position, source_rectangle) tuples that
    specify what piece of the palette image to put where.

    The first image in the list will be drawn first and each later image will
    be alpha-blended on top."""
    if opainter is None:
        tilesize = rects.values()[0].size()
        w, h = statedict.values()[0].shape
        result = QPixmap(QSize(w * tilesize.width(), h * tilesize.height()))
        painter =  QPainter(result)
        painter.scale(tilesize.width(), tilesize.height())
    else:
        painter = opainter

    positions = product(xrange(w), xrange(h))

    values = []
    for pos in positions:
        values.extend(palettizer(statedict, pos))

    fragments = [(QPoint(pos[0], pos[1]), rects[value]) for pos, value in values]

    for dest, src in fragments:
        painter.drawPixmap(QRect(dest, QSize(1, 1)), palette, src)

    if opainter is None:
        return result


dirs = list("ulrd")
def unfinished_serialisation_code(): # {{{ this is unfinished code.
                      #   0      1      2      3
    sets = dict(signal=["str", "sta", "stl", "tun"], # start, state, state_last, turn
                       # 4 5 6 7 
                signal_dir=dirs,
                #        8      9     10      11
                state=["nml", "rel", "fin", "out"], # normal, relaying, finish, outside
                #     4 5 6 7
                direction=dirs, # who do I read from?
                #      12 13 14 15
                payload=list("xyzw"),
                )

    strings = sets["signal"] + dirs + sets["payload"] + sets["state"]

    py_code = """
    is_origin = pos == self.origin_pos

    if is_origin:
        tcmd = self.tape.pop(0)
        if m_state == {out}:
            result_payload = tcmd
            result_state = {nml}
        elif m_state == {nml}:
            if tcmd in [{u}, {l}, {r}, {d}]:
                result_direction = tcmd
                result_state = {rel}
            elif tcmd in [{x}, {y}, {z}, {w}]:
                out_signal = {sta}
                out_signal_dir = m_direction

    else:
        if m_state == {nml}:
            command = out_signal
            out_signal = self.tape.pop(0)
            out_signal_dir = m_direction
    """.format(dict((name, idx) for idx, name in enumerate(strings)))

    computation = PasteComputation(None, py_code)
    tape = Tape([])

    return sets, strings, [computation, tape]
# }}}

def gen_holes(size=(16,16), hole_count=None):
    """This function generates a configuration that has a border of
    "outside configuration" values (-2), a plane of "part of shape" values (-1)
    and `hole_count` holes of -2 somewhere in between.
    There's also a root field (2) in the middle."""
    axis_conf = np.zeros(size, dtype="int")
    image_conf = np.zeros(size, dtype="int")
    sources_conf = np.zeros(size, dtype="int")
    image_conf[:] = -2
    image_conf[1:-1,1:-1] = -1
    image_conf[size[0]/2,size[1]/2] = 2 # root

    if hole_count:
        for hole in random.sample(list(product(xrange(size[0]), xrange(size[1]))), hole_count):
            if image_conf[hole] != 2:
                image_conf[hole] = -2

    return dict(value=image_conf, axis=axis_conf, sources=sources_conf)

def gen_form(size=(16, 16)):
    """This function generates a configuration that has a root (2) in the
    middle and many branching paths that originate there, but never unreachable
    fields."""
    axis_conf = np.zeros(size, dtype="int")
    image_conf = np.zeros(size, dtype="int")
    sources_conf = np.zeros(size, dtype="int")
    image_conf[:] = -2

    image_conf[size[0]/2,size[1]/2] = 2 # root

    for round in xrange((size[0] * size[1]) / 8):
        for pos in product(xrange(1, size[0] - 1), xrange(1, size[1] - 1)):
            if image_conf[pos] != -2:
                continue
            neighs = 0
            for offs in von_neumann_offsets:
                if image_conf[offset_pos(pos, offs)] in (-1, 2):
                    neighs += 1

            if neighs == 1 and random.choice([True, True, False]):
                image_conf[pos] = -1

            if neighs == 2 and random.choice([False, False, False, False, True]):
                image_conf[pos] = -1

    return dict(value=image_conf, axis=axis_conf, sources=sources_conf)

def direction_spread_ca(configuration, output_num):
    """This CA computes paths from all cells to a root cell. It tries to
    optimise flow using a concept called "axis", which spreads an axis from
    the root in all four directions and causes fields to orient themselves
    towards the axis that's next clockwise."""
    # -2 is for outside
    # -1 is the initial state for cells in the image
    # u, l, r and d are for initialised parents
    # m is for the origin cell

    sets = dict(value=[-2, -1, "l", "u", "m", "d", "r"],
                axis=[0, "axis"],
                sources=range(0b1111),
                )
    strings = list("lumdr") + ["axis"]

    pycode = """
    # if we don't compute anything, just keep the previous values.
    result_value = m_value
    result_axis = m_axis
    result_sources = m_sources

    # As soon as the value of a field has been set to something, we no longer
    # care about that field.
    if m_value == -1:
        try:
            # the -2 is there to pad the list so that index corresponds to
            # direction immediately
            origin_dir = [l_value, u_value, 0, d_value, r_value].index(2) # 2 is the root

            # if a 2 is found in the list above, that means one of the
            # neighbour cells is the root.
            # That means we can set our value to the direction and our axis
            # value to "axis"

            result_value = origin_dir
            result_axis = 5 # axis
        except ValueError:
            # The ValueError is thrown by the .index(2) in the try block.
            # If no neighbour is the root, we see if we can decide on a
            # direction.

            # this useful list gives us triplets for each of our neighbours,
            # but only for neighbours that have been initialised to
            # a direction.
            neigh_vals = [
                (dir, val, axis) for (dir, (val, axis))
                in enumerate(zip([l_value, u_value, -2, d_value, r_value],
                                 [l_axis,  u_axis,   0, d_axis,  r_axis]))
                if val >= 0]

            if neigh_vals:
                # if we have any initialised neighbours, see if we have any
                # neighbours with the axis 'bit' set:
                axis_neighbours = filter(lambda (d, v, a): a == 5, neigh_vals)

                # if there's a neighbour that could become our parent without
                # introducing a corner, we will find it in this list.
                # For example, the field to our right is set to "right".
                no_dir_change_neighbours = filter(lambda (d, v, a): d == v, neigh_vals)

                # the same logic for axis_neighbours and no_dir_change_neighbours
                # applies, but the axis neighbours are prioritised above the
                # other ones.
                for arr in (axis_neighbours, no_dir_change_neighbours):
                    if len(arr) == 1:
                        # if we have only one initialised neighbour, it will be
                        # our parent.
                        dir, value, axis = arr[0]
                        result_value = dir
                        # if our only neighbour is an axis and we are also on
                        # that same axis, we set our own axis bit, too.
                        result_axis = 5 if dir == value and axis != 0 else 0
                    elif len(arr) == 2:
                        # if there's two initialised neighbours, we have a
                        # heuristic that causes the 'windmill' pattern to
                        # emerge.
                        arr.sort(key=lambda (d, v, a): v)
                        _, a_v, _ = arr[0]
                        _, b_v, _ = arr[1]
                        if a_v == 1 or b_v == 1:
                            result_value = a_v
                        else:
                            result_value = b_v
                        result_axis = 0

                # if none of the above code changed our value, which can happen
                # if we have 3 or more initialised neighbours,
                if result_value == m_value:
                    # just take the first neighbour we can find.
                    dir, value, axis = neigh_vals[0]
                    result_value = dir
                    result_axis = 0
    elif m_sources == 0 and m_value != -2:
        # if we haven't yet set our sources, we should wait for all neighbours
        # to be set to their final value.

        # all neighbours that have been initialised or are outside-of-shape.
        # iow. all neighbours that have value set to something != -1
        init_neighs = [(dir, val) for (dir, val)
                      in enumerate([l_value, u_value, -2, d_value, r_value])
                      if val != -1]
        if len(init_neighs) == 5:
            for (dir, val) in init_neighs:
                # if the neighbour points back at us, consider it one of
                # our sources.
                if val == 4 - dir:
                    # dir == 2 means (0,0), which doesn't make sense here,
                    # so we subtract 1 for values >= 2.

                    # if dir == 4 and val == 0, that means the cell to our
                    # right reads from its left (which means us)
                    result_sources += 2 ** (dir if dir < 2 else dir - 1)
    """

    directions_palette = QPixmap("images/flow/flow.png")
    images = "lu ru du dl ul rl rd ld ud ur dr lr root white black ax_h ax_v".split(" ")
    rects = dict(enumerate([QRect(x * 64, 0, 64, 64) for x in range(len(images))]))

    def directions_palettizer(states, pos):
        val = states["value"][pos]
        axis = states["axis"][pos]
        sources = states["sources"][pos]

        def rect_for(name, pos=pos):
            return [(pos, images.index(name))]

        if val == -2:
            return rect_for("black")
        elif val == -1:
            return rect_for("white")

        if val == 2:
            return rect_for("white") + rect_for("root")

        result = rect_for("white")
        if axis:
            # 0 == left, 4 == right
            result.extend(rect_for("ax_%s" % ("h" if val in (0, 4) else "v")))

        target_dir_letter = "lu dr"[val]
        other_dir_letter = "rd ul"[val]

        result.extend(rect_for(other_dir_letter + target_dir_letter))

        # make arrows that point from our neighbours to our parent
        for idx in range(4):
            # if the idx'th bit is set in the sources field, add a curved arrow
            if sources & 2 ** idx:
                source_dir_letter = "ludr"[idx]
                result.extend(rect_for(source_dir_letter + target_dir_letter))

        return result

    neigh = SubCellNeighbourhood("lumdr", von_neumann_offsets,
                                 sets.keys())

    loop = TwoDimCellLoop()
    acc = SubcellAccessor(sets.keys())
    computation = PasteComputation(None, pycode)

    size = (16, 16)

    target = SubCellTarget(sets, size, strings, configuration)

    sf = StepFunc(target, loop, acc, neigh, TwoDimConstReader(-2),
                  visitors=[computation])
    sf.gen_code()

    oldconf = target.cconf_value.copy()
    while True:
        # {{{ old string-based draw code
        #vals = str(target.cconf_value.transpose())
        #ax = str(target.cconf_axis.transpose())
        #side_by_side = "\n".join("%s %s" % lines for lines in zip(vals.split("\n"), ax.split("\n")))
        #side_by_side = side_by_side.replace("-2", "  ").replace("-1", " _")
        #print side_by_side
        # }}}
        sf.step()
        if (oldconf != target.cconf_value).any():
            oldconf = target.cconf_value.copy()
        else:
            break
    img = render_state_array_multi_tiled(
            dict(value=target.cconf_value[1:-1,1:-1],
                 axis=target.cconf_axis[1:-1,1:-1],
                 sources=target.cconf_sources[1:-1,1:-1]),
            directions_palettizer,
            directions_palette, rects)
    img.save("klute_%02d.png" % output_num)

for i in range(5):
    direction_spread_ca(gen_holes(hole_count=15*i), i)

for i in range(5):
    direction_spread_ca(gen_form(), 5 + i)

