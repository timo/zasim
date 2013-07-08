# -*- coding: utf8 -*-
from sorting_impl import *
from numpy import *

gridline = Grid1DEuclidean()
#gridtree = GridBinaryTree()

nbh = gridline.use_von_neumann_neighbourhood(radius=1)
#nbh = grid.von_neumann_neighborhood(radius=1)

#? nbh = Neighborhoods.von_neumann(radius=1)   #nbh = Neighborhoods.moore(radius=1)
#? gridline.use_neighborhood(nbh)

#??????? Margolus Nachbarschaft
#??????? Sechseckzellen

#### Ausdehnung
gridline.set_extent(100)


#### Raender
#gridline.use_cyclic_boundaries_handler()
gridline.use_constant_boundaries_handler()  # welche Konstante?
# konstante pro seite?

# definieren, ob randbereiche angezeigt werden sollen oder nicht; wo?

#### Zustandsmenge
# OrderedDict
state = { 'L' : int8, 'R' : int8 }

# oh ich brauch noch mehr, ... auch automatisch
#state['X'] = (-127,-1,0,1,128)
#state['T'] = ('hund', 'katze', 'maus')

#???????? intelligente states?

#### Namen fuer Nachbarn
nbh.direction_names() # left, center, right
#nbn = nbh._names()   # prev, next?
#nbn = nbh._names()   # left right

#### Speicher
#???????? Speicherlayout
mem = DoubleBufferStorage(gridline, state);
#mem = SingleBufferStorage(.....)

#### initial configuration
# abhängig von grid & state, also auf mem?
#mem.init(...??)


#### lokale Regeln
delta_py = """# sort a bit
lr = max(R@left, L@center)
rl = min(L@right, R@center)
L@result, R@result = min(lr, rl), max(lr, rl)"""
#  ??????? Margolusnachbarschaft

# TODO  ^^ new.L etc implementieren, ggf neue syntax?
#       subcell funktionierend machen
#       woher kommt "new"? wie result? wählbar?
#       weave auch

#delta_py = """result = 1"""

#### alles zusammenbauen
za = ZA(gridline, mem, delta_py, base=10)

za.compile_py()
za.display()
#### 
#conf2?? = za.run(conf?, 42)
za.sim.t.cconf_L[0] = -128
za.sim.t.cconf_R[0] = -128
za.sim.t.cconf_L[-1] = 127
za.sim.t.cconf_R[-1] = 127
za.sim.t.nconf_L[0] = -128
za.sim.t.nconf_R[0] = -128
za.sim.t.nconf_L[-1] = 127
za.sim.t.nconf_R[-1] = 127
za.run(100)

# TODO ausgabe spezifizieren und implementieren

# 1d: nach jedem schritt die ganze konfiguration ausgeben
#     ascii grafik kästchen, nur ascii charactere
#     nebeneinander vs untereinander, ...

# 1d animation mit \r in der gleichen zeile

# wie sieht es aus mit datentypen? int8 als zahlen?
# strings? enums, die zahlen auf irgendwas abbilden?
# int8 als braille bitfield?

# beispiel: a1, a2, a3  -  b1, b2, b3  -  ...
#          ?a1,?a2,?a2  -  ...
#          !a1,!a2,!a3  -  ...

# template für die ausgabe?
#[
  #"+-------+",
  #"| {L:2d} {R:2d} |",
  #"|  {XXX:4d}  |",
  #"+-------+",
#]

# farben auf der konsole?

# nur zahlen
# kisten
