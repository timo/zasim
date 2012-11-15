"""This module implements a Computation that handles signal passing between
cells.

A signal is defined as a payload with a direction and each cell has a field
that defines what direction the cell will read from next.

Before the computation, the signal that is sent to this cell is retrieved and
the local variables signal and signal_dir are set.

If there was no signal, both variables will be set to None. If there were
multiple signals addressed to the cell, an Exception is raised.

Setting the out_signal and out_signal_dir variables will send a new signal."""

from .bases import Computation
from .compatibility import no_weave_code

class SignalService(Computation):
    provides_features = [no_weave_code]

    def __init__(self, signal_field="signal",
                       direction_field="sig_dir",
                       read_field="sig_read_dir"):
        self.signal_field = signal_field
        self.direction_field = direction_field
        self.read_field = read_field

    def visit(self):
        self.code.add_py_code("compute",
                """# signal service
                signal = None
                signal_dir = None
                signal_received = False

                out_signal = m_{signal_field}
                out_signal_dir = m_{direction_field}
                out_signal_read_dir = m_{read_field}

                signal_delivery_ok = False""".format(self.__dict__))

        # if we have a signal:
        #   does the neighbour we want to send to read from us?
        #     delete our signal, it will be copied this step.
        #     we can now read from our destination somewhere
        #   does the recipient block us?
        #     set signal_delivery_ok. keep the signal
        #     reset read direction, so that we block other senders
        # if we don't have a signal:
        #   does someone want to send to us?
        #     give them the read direction

        lines = [""]
        put_else = False
        for idx, (neigh, revneighidx) in enumerate(zip(
                self.code.neigh.names,
                map(self.code.neigh.reverse, self.code.neigh.names))):
            revneighname = self.code.neigh.names[revneighidx]
            part = ""
            if put_else: part = "el"
            else:    put_else = True

            part += "if %s_%s == %d: # %s" % (
                        neigh,
                           self.direction_field,
                                 revneighidx,
                                       revneighname)
            if put_else:
                part += "    if signal_received: raise Exception('received signal from multiple sides!')"
            part += "    signal_received = True"
            part += "    signal = %s_%s" % (neigh, self.signal_field)
            part += "    signal_dir = %d # %s" % (revneighidx, revneighname)

            lines.append(part)

        self.code.add_py_code("compute",
                "\n".join(lines))
        self.code.add_py_code("compute", "# end of signal service")

        self.code.add_py_code("compute_reversed",
                """# signal service
                result_%s = out_signal
                result_%s = out_signal_dir""" % (
                    self.signal_field, self.direction_field))

