import random
from zasim.zacformat import ZacSimulator, ZacConsoleDisplay
sim = ZacSimulator(open("example.zac"), (10,))
for x in range(sim.shape[0]):
    sim.cconf["c0l0"][x,0] = random.randint(0,2)
dsp = ZacConsoleDisplay(sim)
dsp.after_step()
for i in range(5):
    sim.step()
