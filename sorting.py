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
gridline.set_extent(4711)


#### Raender
gridline.use_cyclic_boundaries_handler()
#gridtree.use_constant_boundaries_handler()  # welche Konstante?


#### Zustandsmenge
state = { 'L' : int8, 'R' : int8 }

# oh ich brauch noch mehr, ... auch automatisch
#state['X'] = (-127,-1,0,1,128)
#state['T'] = ('hund', 'katze', 'maus')

#???????? intelligente states?


#### Speicher
#???????? Speicherlayout
mem = DoubleBufferStorage(gridline, state, buffer_names=('cur', 'new'))
#mem = SingleBufferStorage(.....)

#### Namen fuer Nachbarn
nbn = nbh.compass_names()
#nbn = nbh._names()   # prev, next?
#nbn = nbh._names()   # left right

#### lokale Regeln
#delta_py = """ new.L = left.L; new.R = new.L + 1 """ #  ??????? Margolusnachbarschaft
delta_py = """ """

#### alles zusammenbauen
za = ZA(gridline, mem, gridline.neigh, delta_py)

za.compile_py()


###########################################################
#### initial configuration
#conf =????

#### 
#conf2?? = za.run(conf?, 42)
za.run(10)


