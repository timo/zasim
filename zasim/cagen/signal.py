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
                       read_field="sig_read_dir",
                       payload_fields=["payload"]):
        self.signal_field = signal_field
        self.direction_field = direction_field
        self.read_field = read_field
        self.payload_fields = payload_fields

    def visit(self):
        set_all_payload_fields = "\n                ".join(
                ["%s = None" % payload_field_name for payload_field_name in
                    self.payload_fields])

        copy_all_payload_fields = "\n                ".join(
                ["out_{0} = m_{0}".format(pf) for pf in self.payload_fields])

        self.code.add_py_code("compute",
                """# signal service
                signal = None
                signal_dir = None
                {payload_field_inits}
                signal_received = False

                out_signal = m_{signal_field}
                out_signal_dir = m_{direction_field}
                out_signal_read_dir = m_{read_field}
                {out_payload_field_inits}

                signal_delivery_ok = False""".format(
                    signal_field=self.signal_field,
                    direction_field=self.direction_field,
                    read_field=self.read_field,
                    payload_field_inits=set_all_payload_fields,
                    out_payload_field_inits=copy_all_payload_fields))

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

        payload_receive_code = "(%s) = [%s][m_%s]" % (
                ",".join(self.payload_fields),
                ",".join(["(%s)" % ",".join([
                          "%s_%s" % (direction, pf)
                            for pf in self.payload_fields])
                    for direction in self.code.neigh.names]),
                self.read_field)


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
                    {payload_receive_code}
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
                    {payload_receive_code}
                    signal_received = True

        """.format(
                dest_neighbour_read_dir=dest_neighbour(self.read_field),
                dest_neighbour_dir=dest_neighbour(self.direction_field),
                src_neighbour_signal=src_neighbour(self.signal_field),
                src_neighbour_dir=src_neighbour(self.direction_field),

                payload_receive_code=payload_receive_code,

                dir_field=self.direction_field
            )
        )

        self.code.add_py_code("compute", "# end of signal service")

        payload_copy_code = "\n                ".join(
                ["result_{0} = out_{0}".format(pf) for pf in self.payload_fields])

        self.code.add_py_code("compute_reversed",
                """# signal service
                result_%s = out_signal
                result_%s = out_signal_dir
                result_%s = out_signal_read_dir

                %s""" % (
                    self.signal_field, self.direction_field, self.read_field,
                    payload_copy_code))

