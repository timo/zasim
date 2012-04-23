from zasim.cagen import ElementarySimulator
from zasim.history import SollertCompressingHistoryStore
from zasim.display.console import OneDimConsolePainter
import numpy as np
import matplotlib.pyplot as plt

import sys

if len(sys.argv) > 1:
    rule = int(sys.argv[1])
else:
    rule = 110

sim = ElementarySimulator(size=(200,), rule=rule)
sollert = SollertCompressingHistoryStore(base=2, sim=sim, store_amount=500)
paint = OneDimConsolePainter(sim, 1)

for i in range(500): sim.step()

print sollert.to_array()
fft = np.abs(np.fft.rfft(sollert.to_array()))
fft = fft[1:] # cut off the first entry, as it is usually a very big number
coordinates = np.arange(len(fft))

plt.plot(coordinates, fft.real, 'b-')
plt.show()

