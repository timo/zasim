# -*- coding: utf8 -*-
from zasim.cagen import *
from zasim.cagen.signal import SignalService

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

def render_state_array_multi_tiled(statedict, palettizer, painter=None):
    if not painter:
        tilesize = rects.values()[0].size()
        result = QPixmap(QSize(w * tilesize.width(), h * tilesize.height()))
        painter =  QPainter(result)
        painter.scale(tilesize.width(), tilesize.height())

    positions = product(xrange(w), xrange(h))

    values = []
    for pos in positions:
        values.extend(palettizer(statedict, pos))

    fragments = [(QPoint(pos[0], pos[1]), rects[value]) for pos, value in values]

    for dest, src in fragments:
        painter.drawPixmap(QRect(dest, QSize(1, 1)), palette, src)

    if not painter:
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
    if m_value == -1:
        try:
            # the -2 is there to pad the list so that index corresponds to
            # direction immediately
            origin_dir = [u_value, l_value, -2, r_value, d_value].index({m})
            result_value = origin_dir
        except ValueError:
            neigh_vals = [
                (dir, val, axis) for (dir, (val, axis))
                in enumerate(zip([u_value, l_value, -2, r_value, d_value],
                                 [u_axis,  l_axis,   0, r_axis,  d_axis]))
                if val >= 0]
            axis_neighbours = filter(lambda d, v, a: a == 1, neigh_vals)
            no_dir_change_neighbours = filter(lambda d, v, a: d == v, neigh_vals)
            if axis_neighbours:
                axis_neighbours.sort(key=lambda d, v, a: v)
                dir, value, axis = axis_neighbours[0]
                result_dir = dir
                result_axis = 0
            elif no_dir_change_neighbours:
                dir, value, axis = no_dir_change_neighbours[0]
                result_dir = dir
                result_axis = axis
            else:
                dir, value, axis = neigh_vals
                result_dir = dir
                result_axis = 0
    """ % dict(m = strings.index("m"))

    computation = PasteComputation(None, pycode)
    return sets, strings, [computation]

directions_palette = QPixmap("images/flow/flow.png")
images = "lu ru du dl ul rl rd ld ud root white black axis".split(" ")
rects = [QRect(x * 64, 0, 64, 64) for x in range(len(images))]

def directions_palettizer(states, pos):
    val = states["value"][pos]
    axis = states["axis"][pos]

    if val == -2:
        return [rects[images.index("black")]]
    elif val == -1:
        return [rects[images.index("white")]]

    if val == 2:
        return [rects[images.index("root")]]
    else:
        result = [rects[images.index("white")]]
        if axis:
            result.append(rects[images.index("axis")])

        # make arrows that point from our neighbours to our parent
        target_dir_letter = "ul rd"[val]
        for idx, offs in enumerate(neigh.offsets):
            val = states["value"][offset_pos(pos, offs)]
            # if this neighbour points at us...
            if val == 4 - idx:
                source_dir_letter = "ul rd"[idx]
                result.append(rects[images.index(target_dir_letter + source_dir_letter)])

        return result

neigh = SubCellNeighbourhood("ulmrd", [(0,-1), (-1,0), (0,0), (1,0), (0,1)],
                             subcells)

loop = TwoDimCellLoop()
acc = SubcellAccessor(sets.keys())
signals = SignalService()

sf = StepFunc(self.target, loop, acc, neigh, BorderSizeEnsurer(),
              visitors=[signals, computation])
