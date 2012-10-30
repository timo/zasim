"""This module implements a Computation that handles signal passing between
cells.

A signal is defined as a payload with a direction.

Before the computation, the signal that is sent to this cell is retrieved and
the local variables signal and signal_dir are set.

If there was no signal, both variables will be set to None. If there were
multiple signals addressed to the cell, an Exception is raised.

Setting the out_signal and out_signal_dir variables will send a new signal."""

from .bases import Computation

class SignalService(Computation):
    def __init__(self, signal_field="signal", direction_field="sig_dir"):
        self.signal_field = signal_field
        self.direction_field = direction_field


signal = None
signal_dir = None
signal_received = False

out_signal = None
out_signal_dir = None
for idx, (n, rn) in enumerate(zip([neighbours_here], [reverse_neighbours_here])):
    if n_sig_dir == rn:
        if signal_received:
            raise Exception("trying to read from %s and %s" % (signal_dir, idx))
        signal = n_signal
        signal_dir = idx
        signal_received = True

[...]

result_signal = out_signal or 0
result_signal_dir = out_signal or -1
