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

        #

        find_neighbour_code = (lambda fieldname:
                lambda remote_field_name:
                    "[%s][%s]" % (
                        ", ".join(["%s_%s" % (name, remote_field_name)
                                   for name in self.code.neigh.names]),
                        "m_%s" % (fieldname))
            )

        dest_neighbour = find_neighbour_code(self.direction_field)
        src_neighbour = find_neighbour_code(self.read_field)

        self.code.add_py_code("compute",
        """#
        if out_signal != 0:
            # if we have a signal:
            #   does the neighbour we want to send to read from us?
            #     delete our signal, it will be copied this step.
            #     we can now read from our destination somewhere
            #   does the recipient block us?
            #     unset signal_delivery_ok. keep the signal
            #     reset read direction, so that we block other senders
            #
            #   does someone send a signal to us?
            #     read the signal
            if {dest_neighbour_read_dir} == self.neigh.reverse_idx(m_{dir_field}):
                signal_delivery_ok = True
                signal = None
                signal_dir = None
                # now we can let the user set a read direction
            else:
                signal_delivery_ok = False

            if {src_neighbour_signal} != 0:
                if {src_neighbour_dir} == self.neigh.reverse_idx(m_{dir_field}):
                    signal = {src_neighbour_signal}
                    signal_dir = self.neigh.reverse_idx({src_neighbour_dir})
                    signal_received = True

        else:
            # if we don't have a signal:
            #   Is someone sending to us from our current read direction?
            #     copy the signal
            #   is there nothing in our read direction?
            #     give the read direction to someone else
            #       we let the user code decide this.
            if {src_neighbour_signal} != 0:
                if {src_neighbour_dir} == self.neigh.reverse_idx(m_{dir_field}):
                    signal = {src_neighbour_signal}
                    signal_dir = self.neigh.reverse_idx({src_neighbour_dir})
                    signal_received = True

        """.format({
            "dest_neighbour_read_dir": dest_neighbour(self.read_field),
            "dest_neighbour_dir": dest_neighbour(self.direction_field),
            "src_neighbour_signal": src_neighbour(self.signal_field),
            "src_neighbour_dir": src_neighbour(self.direction_field),

            "dir_field":self.direction_field,
            })
        )

        self.code.add_py_code("compute", "# end of signal service")

        self.code.add_py_code("compute_reversed",
                """# signal service
                result_%s = out_signal
                result_%s = out_signal_dir""" % (
                    self.signal_field, self.direction_field))

