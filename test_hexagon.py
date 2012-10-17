from zasim.display.qt import cut_hexagons, generate_tile_atlas, TwoDimQImagePalettePainter
from zasim.cagen.simulators import ElementarySimulator
from zasim.cagen.neighbourhoods import AlternatingNeighbourhood
from os import path
from PySide.QtGui import *
from PySide.QtCore import *
from zasim.gui.display import DisplayWidget
from zasim.gui.control import ControlWidget
from zasim.gui.mainwin import ZasimMainWindow
from zasim import config

nameStateDict = { "U": 0,
                  #"C00" : 2048, "C10" : 2049, "C01" : 2050, "C11" : 2051,
                  "C00" : 1, "C10" : 2, "C01" : 3, "C11" : 4,
                  "S"   : 4096, "S0"  : 4128, "S1"  : 4144, "S00" : 4160,
                  "S01" : 4168, "S10" : 4176, "S11" : 4184, "S000": 4192,
                  "T000": 6144, "T001": 6272, "T010": 6400, "T011": 6528,
                  "T020": 6656, "T032": 6784, "T030": 6912, "T031": 7040,
                  "T100": 7168, "T101": 7296, "T110": 7424, "T111": 7552,
                  "T120": 7680, "T121": 7808, "T130": 7936, "T131": 8064 }
stateNameDict = {a:b for b,a in nameStateDict.iteritems()}
states = sorted(nameStateDict.values())
filename_map = {num:path.join("images/vonNeumann", stateNameDict[num]) + ".png" for num in states}

image, rects = generate_tile_atlas(filename_map, "images/vonNeumann")

image = cut_hexagons(image, rects)

def HexagonalNeighbourhood(Base=AlternatingNeighbourhood, **kwargs):
    return Base("lu ru l m r ld rd".split(" "),
                [[(-1, -1), (0, -1),
                  (-1, 0), (0, 0), (1, 0),
                  (-1, 1), (0, 1)],
                 [(0, -1), (1, -1),
                  (-1, 0), (0, 0), (1, 0),
                  (0, 1), (1, 1)]])

config = config.RandomConfiguration(2, 0.9, 0.1)
sim = ElementarySimulator(base=2, size=(20,20), config=config, neighbourhood=HexagonalNeighbourhood)
sim.palette_info["tiles"] = {}
sim.palette_info["tiles"]["images"] = image
sim.palette_info["tiles"]["rects"] = rects
sim.t.possible_values = (0, 1)

painter = TwoDimQImagePalettePainter(sim, hexagonal=True)

display = DisplayWidget(sim, painter=painter, scale=0.25)

cnt = ControlWidget(sim)

mainwin = ZasimMainWindow(sim, display, cnt)
mainwin.show()

qApp.exec_()
