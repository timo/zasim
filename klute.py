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

    computation = PasteComputation(None, py_code)
    return sets, strings, [computation]

neigh = SubCellNeighbourhood("ulmrd", [(0,-1), (-1,0), (0,0), (1,0), (0,1)],
                             subcells)

loop = TwoDimCellLoop()
acc = SubcellAccessor(sets.keys())
signals = SignalService()

sf = StepFunc(self.target, loop, acc, neigh, BorderSizeEnsurer(),
              visitors=[signals, computation])
