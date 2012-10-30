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
    pass

