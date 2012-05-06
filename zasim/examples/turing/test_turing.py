from zasim.examples.turing import main

class TestTuringCa(object):
    def test_turing_main(self):
        main.main()

    def test_turing_step(self):
        tape = main.TuringTapeSimulator()
        start_conf = tape.get_config().copy()
        tape.step()
        end_conf = tape.get_config().copy()

        for index in range(tape.shape[0] - 1):
            # if there's a signal in the field now, the data in the signal
            # will have been in the top half of the field in the previous
            # step.
            if end_conf[index] % 4 != 3:
                assert end_conf[index] % 4 == start_conf[index] / 4

