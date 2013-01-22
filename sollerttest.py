from zasim.cagen import ElementarySimulator
from zasim.history import SollertCompressingHistoryStore
from zasim.display.console import OneDimConsolePainter
import numpy as np
import matplotlib.pyplot as plt

import sys

averaging_repeats = 200

sim_world_width = 200
sollert_world_width = 100
sollert_history_len = 500
sim_step_amount = sollert_history_len
display_sim_on_console = True
display_sollert_data = True

if len(sys.argv) > 1:
    rule = int(sys.argv[1])
else:
    rule = 110

def do_one_repeat():
    sim = ElementarySimulator(size=(sim_world_width,), rule=rule)
    sollert = SollertCompressingHistoryStore(
            base=2,
            sim=sim,
            store_amount=sollert_history_len,
            width=sollert_world_width)

    if display_sim_on_console:
        paint = OneDimConsolePainter(sim, 1)

    for i in range(sim_step_amount): sim.step()

    if display_sollert_data:
        print sollert.to_array()

    fft = np.fft.rfft(sollert.to_array())
    fft = np.abs(fft) # make all peaks positive
    fft = fft[1:] # cut off the first entry, as it is usually a very big number

    return fft

value = None
for i in range(averaging_repeats):
    result = do_one_repeat()
    if value is None:
        value = result
    else:
        value += result

value = value / averaging_repeats

coordinates = np.arange(len(value))

plt.plot(coordinates, value, 'b-')
plt.show()

