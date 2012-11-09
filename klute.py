# -*- coding: utf8 -*-
from zasim.cagen import *
from zasim.cagen.signal import SignalService
from zasim.external.qt import QPixmap, QPainter, QRect, QSize, QPoint
from time import sleep

import numpy as np

class Tape(StepFuncVisitor):
    def __init__(self, content):
        self.initial_content = list(content)

    def visit(self):
        self.code.attrs.append("tape")

    def set_target(self, target):
        super(Tape, self).set_target(target)
        self.target.tape = self.initial_content.copy()

class HasOrigin(StepFuncVisitor):
    def __init__(self, origin_pos):
        self.origin_pos = origin_pos

    def visit(self):
        self.code.attrs.append("origin_pos")

    def set_target(self, target):
        super(HasOrigin, self).set_target(target)
        self.target.origin_pos = self.origin_pos.copy()

def render_state_array_multi_tiled(statedict, palettizer, palette, rects, opainter=None):
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
def unfinished_serialisation_code():
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

def direction_spread_ca():
    # -2 is for outside
    # -1 is the initial state for cells in the image
    # u, l, r and d are for initialised parents
    # m is for the origin cell
    sets = dict(value=[-2, -1, "u", "l", "m", "r", "d"],
                axis=[0, "axis"]
                )
    strings = list("ulmrd") + ["axis"]

    pycode = """
    result_value = m_value
    result_axis = m_axis
    if m_value == -1:
        try:
            # the -2 is there to pad the list so that index corresponds to
            # direction immediately
            origin_dir = [u_value, l_value, 0, r_value, d_value].index(2) # 2 is the root

            result_value = origin_dir
            result_axis = 5 # axis
        except ValueError:
            neigh_vals = [
                (dir, val, axis) for (dir, (val, axis))
                in enumerate(zip([u_value, l_value, -2, r_value, d_value],
                                 [u_axis,  l_axis,   0, r_axis,  d_axis]))
                if val >= 0]
            if neigh_vals:
                axis_neighbours = filter(lambda (d, v, a): a == 5, neigh_vals)
                no_dir_change_neighbours = filter(lambda (d, v, a): d == v, neigh_vals)

                for arr in (axis_neighbours, no_dir_change_neighbours):
                    if len(arr) == 1:
                        dir, value, axis = arr[0]
                        result_value = dir
                        result_axis = 5 if dir == value and axis != 0 else 0
                    elif len(arr) == 2:
                        arr.sort(key=lambda (d, v, a): v)
                        _, a_v, _ = arr[0]
                        _, b_v, _ = arr[1]
                        if (a_v, b_v) == (0, 3) or (a_v, b_v) == (3, 4):
                            result_value = a_v
                        else:
                            result_value = b_v
                        result_axis = 0
                if result_value == m_value:
                    dir, value, axis = neigh_vals[0]
                    result_value = dir
                    result_axis = 0
    """

    directions_palette = QPixmap("images/flow/flow.png")
    images = "lu ru du dl ul rl rd ld ud ur dr lr root white black axis".split(" ")
    rects = dict(enumerate([QRect(x * 64, 0, 64, 64) for x in range(len(images))]))

    def directions_palettizer(states, pos):
        val = states["value"][pos]
        axis = states["axis"][pos]

        def rect_for(name, pos=pos):
            return [(pos, images.index(name))]

        if val == -2:
            return rect_for("black")
        elif val == -1:
            return rect_for("white")

        if val == 2:
            return rect_for("root")
        else:
            result = rect_for("white")
            if axis:
                result.extend(rect_for("axis"))
                print "axis",

            target_dir_letter = "ul rd"[val]
            other_dir_letter = "dr lu"[val]

            result.extend(rect_for(other_dir_letter + target_dir_letter))

            print "t:", target_dir_letter,

            # make arrows that point from our neighbours to our parent
            for idx, offs in enumerate(neigh.offsets):
                oval = states["value"][offset_pos(pos, offs)]
                # if this neighbour points at us...
                if oval == 4 - idx:
                    print "ov:", oval, "idx", idx,
                    source_dir_letter = "ul rd"[oval]
                    result.extend(rect_for(source_dir_letter + target_dir_letter))

            print
            return result

    neigh = SubCellNeighbourhood("ulmrd", [(0,-1), (-1,0), (0,0), (1,0), (0,1)],
                                 sets.keys())

    loop = TwoDimCellLoop()
    acc = SubcellAccessor(sets.keys())
    signals = SignalService()
    computation = PasteComputation(None, pycode)

    size = (16, 16)
    axis_conf = np.zeros(size, dtype="int")
    image_conf = np.zeros(size, dtype="int")
    image_conf[:] = -2
    image_conf[1:-1,1:-1] = -1
    image_conf[5,5] = 2 # root

    configs = dict(value=image_conf, axis=axis_conf)

    target = SubCellTarget(sets, size, strings, configs)

    sf = StepFunc(target, loop, acc, neigh, TwoDimConstReader(-2),
                  visitors=[computation])
    sf.gen_code()
    for i in range(20):
        #vals = str(target.cconf_value.transpose())
        #ax = str(target.cconf_axis.transpose())
        #side_by_side = "\n".join("%s %s" % lines for lines in zip(vals.split("\n"), ax.split("\n")))
        #side_by_side = side_by_side.replace("-2", "  ").replace("-1", " _")
        #print side_by_side
        sf.step()
        img = render_state_array_multi_tiled(
                dict(value=target.cconf_value[1:-1,1:-1], axis=target.cconf_axis[1:-1,1:-1]),
                directions_palettizer,
                directions_palette, rects)
        img.save("klute_%02d.png" % i)

direction_spread_ca()
