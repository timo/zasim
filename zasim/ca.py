#!/usr/bin/python
from __future__ import absolute_import

import numpy as np
import random
import re

try:
    from scipy import weave
    from scipy.weave import converters
    HAVE_WEAVE = True
except:
    print "weave is not available."
    HAVE_WEAVE = False

try:
    a = np.zeros((100,), int)
except TypeError:
    print "using integer array compatibility with float arrays"
    old_zeros = np.zeros
    def compatibility_zeros(*args):
        try:
            return old_zeros(args[0])
        except TypeError:
            return old_zeros(args[0][0])
    np.zeros = compatibility_zeros

try:
    import pygame
except ImportError:
    # if pygame isn't installed, at least get the modifier values.
    class pygame(object):
        KMOD_ALT = 768
        KMOD_CAPS = 8192
        KMOD_CTRL = 192
        KMOD_LALT = 256
        KMOD_LCTRL = 64
        KMOD_LMETA = 1024
        KMOD_LSHIFT = 1
        KMOD_META = 3072
        KMOD_MODE = 16384
        KMOD_NONE = 0
        KMOD_NUM = 4096
        KMOD_RALT = 512
        KMOD_RCTRL = 128
        KMOD_RMETA = 2048
        KMOD_RSHIFT = 2
        KMOD_SHIFT = 3


## @package CA.py
#
# Provides us with classes for cellular automata. If a new automaton is to be implemented,
# it should find it's place here as well.

class ConfigurationImportError(Exception): pass
class ConfigurationParseError(ConfigurationImportError): pass

## Provides stuff like import/export functions, getter methods and resizing
class CA(object):
    ## When passed as parameter, the configuration is filled with zeros
    INIT_ZERO = 0
    ## When passed as parameter, the configuration is filled with ones
    INIT_ONES = 1
    ## When passed as parameter, the configuration is filled randomly
    INIT_RAND = 2
    ## When passed as parameter, the configuration is imported from a given file
    INIT_FILE = 3

    ## Returnflag when importing a configuration from file
    IMPORTOK = 0
    ## Returnflag when importing a configuration from file
    SIZECHANGED = 1
    ## Returnflag when importing a configuration from file
    WRONGCA = 2
    ## Returnflag when importing a configuration from file
    IMPORTNOTOK = 3

    ## Tells the Display module how to show each state
    palette = []

    ## Is executed when the user clicks on a cell
    def click_on_cell( self, x, y, mousekey, modifiers ):
        print "function clickOnCell() for", self.getTitle(), "not implemented yet"

    ## Is executed when the user hits a key
    # this is currently not connected to anything
    def keyboard_hit( self, x, y, key, modifiers ):
        print "function keyboard_hit() for", self.getTitle(), "not implemented yet"

    ## Exports the current configuration to a file in XASIM-format.
    # The first lines states the width, the next line the height, if the cellular automaton is 2 dimensional,
    # the configuration itself beginning after that, consists all cell's states in a row,
    # row by row, so the shape of the configuration file is the same as the configuration itself.
    # Notice the ghostcells at the borders!
    # \verbatim
    # Example:
    # 4                // width
    # 5                // height
    # (0)(0)(0)(0)(0)  // here starts the configuration
    # (0)(2)(0)(3)(0)  // number of cols is witdh
    # (0)(2)(1)(2)(0)  // number of lines is height
    # (0)(0)(0)(0)(0)
    # SANDPILE
    # \endverbatim
    def exportConf( self, filename ):
        with open( filename, 'w' ) as f:
            # sizeX
            f.write( str(self.sizeX) + "\n" )
            # sizeY
            if self.getDim() > 1:
                f.write( str(self.sizeY) + "\n" )
                # conf
                for j in range(self.sizeY):
                    for i in range(self.sizeX):
                        f.write( "(" + str(self.currConf[i][j]) + ")" )
                    f.write( "\n" )
            else:
                for i in range(self.sizeX):
                    f.write( "(" + str(self.currConf[i][0]) + ")" )
                f.write( "\n" )
            f.write( self.getType() + "\n" )
            f.close()

    ## Returns the type of the cellular automaton.
    # It's a upper-cased version of CA::title, used to identify it internally as one or
    # another cellular automaton.
    def getType( self ):
        return self.title.upper()

    ## Returns the current configuration
    def get_config( self ):
        return self.currConf.copy()

    ## Returns the cellular automaton's dimension
    def getDim( self ):
        return self.dim

    ## Returns the cellular automaton's size as (height,width)
    def getSize( self ):
        return self.size

    ## Returns the cellular automaton's title.
    # It's a non-upper-cased version of CA::title, used to display it in the titlebar
    def getTitle( self ):
        return self.title

    ## Imports a configuration from a file in XASIM-Format.
    # For XASIM-Format, see CA::exportConf.
    # For vonNeumann cellular automaton, RLE-files are supported as well (see vonNeumann::importConf).
    def importConf( self, filename ):
        retVal = self.IMPORTOK
        with open( filename, 'r' ) as f:
            lines = f.readlines()
            CAImportType = lines[-1][:-1]
            f.close()
            if CAImportType != self.getType():
                raise ConfigurationImportError("Tried importing a %s into an %s." % 
                        (CAImportType, self.getType()))
            f = open( filename, 'r' )
            # sizeX
            sizeX = f.readline().strip()
            try:
                sizeX = int(sizeX)
            except ValueError:
                raise ConfigurationImportError("Expected y dimension size as integer, got %r instead" % sizeX)

            if self.getDim() > 1:
                # sizeY
                sizeY = f.readline().strip()
                try:
                    sizeY = int(sizeY)
                except ValueError:
                    raise ConfigurationImportError("Expected y dimension size as integer, got %r instead" % sizeY)
                if sizeX != self.sizeX or sizeY != self.sizeY:
                    self.resize( sizeX, sizeY )
                    retVal = self.SIZECHANGED

            else:
                sizeY = 1
                if sizeX != self.sizeX:
                    self.resize( sizeX )
                    retVal = self.SIZECHANGED

            importRegexp = re.compile("\((\d*)\)")
            for j in range(sizeY):
                content = ['', '', f.readline()[0:-1]]
                for i in range(sizeX):
                    content = importRegexp.split( content[2], 1 )
                    try:
                        state = int(content[1])
                    except ValueError:
                        raise ConfigurationParseError("Could not parse line. %r" %
                                content)
                    self.currConf[i][j] = state
        self.nextConf = self.currConf.copy()
        return retVal

    ## Is called in every step of the simulation.
    def loopFunc( self ):
        print "function loopFunc() not implemented yet"

    ## Prototype... Not really implemented yet
    def quit( self ):
        print "function quit() not implemented yet"

    ## Resizing the cellular automaton.
    # Not in use right now,
    def resize( self, sizeX, sizeY = None ):
        ## width of the ca
        self.sizeX = sizeX
        if sizeY == None:
            sizeY = self.sizeY
        else:
            ## height of the ca
            self.sizeY = sizeY
        ## the ca's size as (width,height)
        self.size = sizeX,sizeY
        if self.getDim() == 1:
            ## The current configuration is stored here
            self.currConf = np.zeros( sizeX )
            ## The next step's configuration is stored here (ping-ponging!).
            self.nextConf = np.zeros( sizeX )
        elif self.getDim() == 2:
            self.currConf = np.zeros( self.size )
            self.nextConf = np.zeros( self.size )

    ## Set the current configuration to conf.
    # This is used when switching between marked configurations and cellular automaton types.
    # @param conf The configuration to load.
    def setConf( self, conf ):
        self.currConf = conf.copy()
        self.nextConf = conf.copy()


## A cellular automaton that simulates all one dimensional binary rule cellular automaton,
# such as Rule 110. CA::binRule handles all one dimenasional binary cellular automaton
# with the neighbourhood (-1,0,1).
class binRule( CA ):
    palette = [ (0,0,0), (255,255,255) ]
    ## constructor
    # TODO remove the unnecessary sizeY argument
    def __init__ ( self, ruleNr, sizeX, sizeY, initConf, filename=""):
        ## The dimension of binRule
        self.dim = 1
        if not 0 <= ruleNr < 256:
            raise ValueError("binRule only supports ruleNr between 0 and 255!")

        ## The rulenumber in decimal notation ( in [0;255] )
        self.ruleNr = ruleNr
        self.sizeX = sizeX
        self.sizeY = sizeY
        self.size = ( sizeX, sizeY )
        ## The title of the ca
        self.title = "Rule" + str( self.ruleNr )

        if initConf == self.INIT_ZERO:
            self.currConf = np.zeros(sizeX, int)
        elif initConf == self.INIT_ONES:
            self.currConf = np.ones(sizeX, int)
        elif initConf == self.INIT_RAND:
            self.currConf = np.zeros(sizeX, int)
            for i in range( sizeX ):
                self.currConf[i] = random.randint( 0, 1 )
        else:
            raise ValueError("Initflag not supported for %s. Supported flags are:\n" +
                "INIT_ZERO, INIT_ONES, INIT_RAND, INIT_FILE + filename" %
                self.getType())

        self.setConf(self.currConf)

        if filename != "":
            self.importConf( filename )

        ## An array that contains the value table for this particular binary transition rule
        self.ruleIdx = np.zeros( 8 )
        for i in range( 8 ):
            if ( self.ruleNr & ( 1 << i ) ):
                self.ruleIdx[i] = 1

    def getType( self ):
        return self.title.upper() + str(self.ruleNr)

    def loopFunc( self ):
        self.step()

    def setConf( self, conf ):
        self.currConf = conf.copy()
        self.currConf[0] = self.currConf[-2]
        self.currConf[-1] = self.currConf[1]
        self.nextConf = self.currConf.copy()

    ## What to do in every step.
    # sets loopFunc to the appropriate update function
    def step( self ):
        try:
            self.updateAllCellsWeaveInline()
            self.loopFunc = self.updateAllCellsWeaveInline
        except:
            self.updateAllCellsPy()
            self.loopFunc = self.updateAllCellsPy

    ## Updates all cells in plain python.
    def updateAllCellsPy( self ):
        ## this will eventually be really fast in pypy,
        ## but at the moment, the garbage collector will use big amounts of
        ## memory

        #result = self.currConf[:-2] * 4 + self.currConf[1:-1] * 2 + self.currConf[2:]
        #index = 0
        #for value in result:
            #state = int(value)
            #self.nextConf[index+1] = ((1 << state) & self.ruleNr) >> state
            #index += 1

        for i in range( 1, self.sizeX-1 ):
            state =  self.currConf[i-1] * 4
            state += self.currConf[i] * 2
            state += self.currConf[i+1]
            state = int(state)
            self.nextConf[i] = ((1 << state) & self.ruleNr) >> state

        self.nextConf[0] = self.nextConf[self.sizeX-2]
        self.nextConf[self.sizeX-1] = self.nextConf[1]
        self.currConf, self.nextConf = self.nextConf, self.currConf

    ## Updates all cells using scipy.weave.inline for faster execution
    def updateAllCellsWeaveInline( self ):
        binRuleCode = """
#include <stdio.h>
#line 1 "CA.py"
int i;
int state;
for ( i = 1; i < sizeX-1; i++ ) {
  state =  cconf(i-1) << 2;
  state += cconf(i  ) << 1;
  state += cconf(i+1);
  nconf(i) = rule(state);
}
nconf(0) = nconf(sizeX-2);
nconf(sizeX-1) = nconf(1);
"""
        cconf = self.currConf
        nconf = self.nextConf
        sizeX = self.sizeX
        rule = self.ruleIdx
        weave.inline( binRuleCode, ['cconf', 'nconf', 'sizeX', 'rule'],
                      type_converters = converters.blitz,
                      compiler = 'gcc' )
        self.currConf, self.nextConf = self.nextConf, self.currConf

## The SandPile cellular automaton
class sandPile( CA ):

    #black = 0,0,0
    #white = 255,255,255
    #red = 255,0,0
    #green = 0,255,0
    #blue = 0,0,255
    #grey = 170,170,170
    #pink = 250,40,230
    #darkred = 95,0,16
    #yellow = 255,240,0

#    palette = [blue, white, yellow, darkred, grey, pink, green, red]
    palette = [(0, 0, 0), (32, 32, 32), (64, 64, 64), (96, 96, 96),
               (128, 128, 128), (160, 160, 160), (192, 192, 192), (224, 224, 224)]

    ## Histogram info for each state
    info = ( "state 0", "state 1", "state 2", "state 3",
             "state 4", "state 5", "state 6", "state 7" )
    ## The constructor
    def __init__( self, sizeX, sizeY, initConf, filename="" ):
        ## The ca's dimension
        self.dim = 2
        ## The ca's title
        self.title = "Sandpile"
        self.size = self.sizeX,self.sizeY = sizeX,sizeY

        ## The histogram over all states in the ca, as numpy.array.
        # Containing the absolute frequency of each state
        self.histogram = np.zeros( 8, int )

        if initConf == self.INIT_ZERO:
            self.currConf = np.zeros( ( sizeX, sizeY ), int )
            self.nextConf = np.zeros( ( sizeX, sizeY ), int )
            self.histogram[ 0 ] = self.sizeX * self.sizeY
        elif initConf == self.INIT_RAND:
            self.currConf = np.zeros( ( sizeX, sizeY ), int )
            for x in range( 1, sizeX-1 ):
                for y in range( 1, sizeY-1 ):
                    c = random.randint( 0, 3 )
                    self.currConf[ x, y ] = c
                    self.histogram[ c ] += 1
            self.nextConf = self.currConf.copy()
        else:
            raise ValueError("Initflag not supported for %s. Supported flags are:\n" +
                "INIT_ZERO, INIT_RAND, INIT_FILE + filename" %
                self.getType())

        if filename != "":
            self.importConf( filename )

    ## Since a sandPile ca runs out of activity eventually if no grains are added, it has to
    # happen once in a while.
    # @param x X-coordinate where to add a grain
    # @param y Y-coordinate where to add a grain
    def addGrain( self, x, y ):
        if not ( (x > self.sizeX - 1) or (y > self.sizeY - 1) ):
            if self.currConf[ x, y ] < 7:
                self.currConf[ x, y ] += 1

    ## Randomly throws a new grain into the configuration
    def addGrainRandomly( self ):
        x = random.randint( 1, self.sizeX-1 )
        y = random.randint( 1, self.sizeY-1 )
        while self.currConf[ x, y ] >= 7:
            x = random.randint( 1, self.sizeX-1 )
            y = random.randint( 1, self.sizeY-1 )
        self.currConf[ x, y ] += 1

    ## What happens when a event occurs?
    # When the left mousebutton is clicked on a cell, a grain is added to that, a right-click
    # resets the cell's state to 0.
    def click_on_cell( self, x, y, mousekey, modifiers ):
        if mousekey == 1:
            self.addGrain( x, y )
        if mousekey == 3:
            self.setState( x, y, 0 )

    ## Returns a histogram over the ca's states.
    def getHistogram( self ):
        # making histogram
        #
        # note: when importing a new conf from file, a new histogram has to
        # be counted!
        # ( in case there has been made a change in that matter )
        self.histogram = np.histogram( self.currConf,
                                       bins=np.arange(8),
                                       normed=True )[0]
        return self.histogram

    def loopFunc( self ):
        self.addGrain( self.sizeX/2, self.sizeY/2 )
#        self.addGrainRandomly()
        self.step()

    def quit( self ):
        self.closeHistograms()

    ## Set a cell's state to s
    def setState( self, x, y, s ):
        if 0 <= s < 8 and 0 < x < (self.sizeX-1) and 0 < y < (self.sizeY-1):
            self.currConf[ x, y ] = s
            self.nextConf[ x, y ] = s


    ## What to do in every step.
    # Calls sandPile::updateAllCellsWeaveInline, that uses scipy.weave.inline
    def step( self ):
        self.updateAllCellsWeaveInline()

    ## Updates all cells in plain python and calclulates the new histogram, too.
    def updateAllCellsPyHistImpl( self ):
        for x in range( 1, self.sizeX-1 ):
            for y in range( 1, self.sizeY-1 ):
                if self.currConf[ x, y ] > 3:
                    self.nextConf[ x, y ] = self.currConf[ x, y ] - 4
                    self.nextConf[ x+1, y ] = self.currConf[ x+1, y ] + 1
                    self.nextConf[ x-1, y ] = self.currConf[ x-1, y ] + 1
                    self.nextConf[ x, y+1 ] = self.currConf[ x, y+1 ] + 1
                    self.nextConf[ x, y-1 ] = self.currConf[ x, y-1 ] + 1
                else:
                    self.nextConf[ x, y ] = self.currConf[ x, y ]
        self.currConf,self.nextConf = self.nextConf,self.currConf

    ## Updates all cells in plain python without calculating the new histogram.
    def updateAllCellsPyHistExpl( self ):
        for x in range( 1, self.sizeX-1 ):
            for y in range( 1, self.sizeY-1 ):
                if self.currConf[ x, y ] > 3:
                    self.nextConf[ x, y ] = self.currConf[ x, y ] - 4
                    self.nextConf[ x+1, y ] = self.currConf[ x+1, y ] + 1
                    self.nextConf[ x-1, y ] = self.currConf[ x-1, y ] + 1
                    self.nextConf[ x, y+1 ] = self.currConf[ x, y+1 ] + 1
                    self.nextConf[ x, y-1 ] = self.currConf[ x, y-1 ] + 1
        self.currConf = self.nextConf.copy()

    ## Updates all cells using scipy.weave.inline
    def updateAllCellsWeaveInline( self ):
        sandpileCode = """
#line 1 "CA.py"
int i, j;
for ( i = 1; i < sizeX-1; i++ ) {
  for ( j = 1; j < sizeY-1; j++ ) {
    nconf(i,j)  = cconf(i,  j  ) & 3;
    nconf(i,j) += cconf(i-1,j  ) >> 2;
    nconf(i,j) += cconf(i+1,j  ) >> 2;
    nconf(i,j) += cconf(i,  j-1) >> 2;
    nconf(i,j) += cconf(i,  j+1) >> 2;
  }
}
"""
        cconf = self.currConf
        nconf = self.nextConf
        sizeX = self.sizeX
        sizeY = self.sizeY
        weave.inline( sandpileCode, ['cconf', 'nconf', 'sizeX', 'sizeY' ],
                      type_converters = converters.blitz,
                      compiler = 'gcc' )
        self.currConf = self.nextConf.copy()





## Exactly the same as sandPile, but has an image of a cat as starting configuration
# XXX: what is this?
class catPile( sandPile ):
    ## The constructor
    def __init__( self, sizeX, sizeY, initConf ):
        self.readImage( "cat.jpg" )

    ## Reads the image of a cat that is being used as starting configuration
    def readImage( self, filename ):
        dummy_data = Image.open(filename)
        dummy_data = dummy_data.convert("I")

        image = pilutil.fromimage(dummy_data)
        for i in range(len(image)):
            for j in range(len(image[0])):
                image[i,j] /= 32
        self.currConf = image
        self.nextConf = image
        i = np.transpose(image)
        self.currConf = np.transpose(image)
        self.nextConf = self.currConf.copy()

    def getTitle( self ):
        return "CatPile"

## The cellular automaton proposed by John von Neumann
# \verbatim
# All states are encoded in a bitmask:
#
#    <--MSB                     10                              LSB
#  ...... 0 0 0 0 0 0 0 0 0 X X u a1 a0 eps sc1 sc0 s2 s1 s0 e1 e0
#                           | | | |  |  |    |   |   |  |  |  |  |-> current e
#  XX = 00 -> U    <--------| | | |  |  |    |   |   |  |  |  |----> next e
#  XX = 01 -> C    <----------| | |  |  |    |   |   |  |  |
#  XX = 10 -> S                 | |  |  |    |   |   |  |  |-------> lsb on S
#  XX = 11 -> T                 | |  |  |    |   |   |  |----------> ...
#                               | |  |  |    |   |   |-------------> msb on S
#  S{} is encoded as SMASK_111  | |  |  |    |   |-----------------> s-state counter
#                               | |  |  |    |---------------------> s-state counter
#                               | |  |  |
#                               | |  |  |--------------------------> excited
#                               | |  |-----------------------------> direction
#                               | |--------------------------------> direction
#                               |----------------------------------> special
#
# \endverbatim
class vonNeumann ( CA ):
    palette = []
    ## The constructor
    def __init__( self, sizeX, sizeY, confFile ):
        ## The ca's title
        self.title = "vonNeumann"
        ## The ca's dimension
        self.dim = 2
        self.size = self.sizeX, self.sizeY = sizeX, sizeY

        ## A map from states according to the bitmask to
        # pygame blittable states ( between 0 and 28 )
        self.displayableStateDict = {
            0: 0,     # U
            2048: 1,  #C00   2048
            2049: 2,  #C10   2048+1
            2050: 3,  #C01   2048+2
            2051: 4,  #C11   2048+3
            4192: 5,  #S000  4096+96
            4160: 6,  #S00   4096+64
            4168: 7,  #S01   4096+64+8
            4128: 8,  #S0    4096+32
            4176: 9,  #S10   4096+64+16
            4184: 10, #S11   4096+64+16+8
            4144: 11, #S1    4096+32+16
            4096: 12, #S     4096
            6144: 13, #T000  6144
            6272: 14, #T001  6144+128
            6400: 15, #T010  6144+256
            6528: 16, #T011  6144+128+256
            6656: 17, #T020  6144+512
            6784: 18, #T021  6144+128+512
            6912: 19, #T030  6144+256+512
            7040: 20, #T031  6144+128+256+512
            7168: 21, #T100  6144+1024
            7296: 22, #T101  6144+128+1024
            7424: 23, #T110  6144+256+1024
            7552: 24, #T111  6144+128+256+1024
            7680: 25, #T120  6144+512+1024
            7808: 26, #T121  6144+128+512+1024
            7936: 27, #T130  6144+256+512+1024
            8064: 28, #T131  6144+128+256+1024+512
            }

        ## A map from human readable vonNeumann states ( such as 'U', 'T020' and 'C11' )
        # actual states calculated via bitmask
        self.nameStateDict = { "U": 0,
                               "C00" : 2048, "C10" : 2049, "C01" : 2050, "C11" : 2051,
                               "S"   : 4096, "S0"  : 4128, "S1"  : 4144, "S00" : 4160,
                               "S01" : 4168, "S10" : 4176, "S11" : 4184, "S000": 4192,
                               "T000": 6144, "T001": 6272, "T010": 6400, "T011": 6528,
                               "T020": 6656, "T032": 6784, "T030": 6912, "T031": 7040,
                               "T100": 7168, "T101": 7296, "T110": 7424, "T111": 7552,
                               "T120": 7680, "T121": 7808, "T130": 7936, "T131": 8064 }

        ## An array containing all correct states (see vonNeumann)
        self.states = [ 0, 2048, 2049, 2050, 2051, 4096, 4128, 4144, 4160, 4168,
                        4176, 4184, 4192, 6144, 6272, 6400, 6528, 6656, 6784,
                        6912, 7040, 7168, 7296, 7424, 7552, 7680, 7808, 7936, 8064 ]

        ## The current configuration is held here
        # as usual, these two arrays contain the real configuration, that is used
        # in every step ... (see vonNeumann::displayConf)
        self.currConf = np.zeros( (sizeX, sizeY), int )
        ## The current configuration is held here
        self.nextConf = np.zeros( (sizeX, sizeY), int )
        # used when updating only some cells instead of all....
        self.cActArr = np.zeros( (self.sizeX*self.sizeY), bool )
        self.nActArr = np.zeros( (self.sizeX*self.sizeY), bool )
        self.cList = np.zeros( (self.sizeX*self.sizeY), int )
        self.nList = np.zeros( (self.sizeX*self.sizeY), int )
        self.cCounter = 0
        self.nCounter = 0
        if confFile != "":
            self.importConf( confFile )
            self.nextConf = self.currConf.copy()
        ## The configuration that is blittet...
        # But in this CA the states are not enumerable from 0..28, but scattered
        # between 0 and ~2^13, so we need a dict (see vonNeumann::displayableStateDict)
        # to map the states to 0..28, so the Display-module can display states
        # without knowing the difference
        self.displayConf = np.zeros( self.size, int)


        for imgFile in ( "images/vonNeumann/U.jpg",    "images/vonNeumann/C00.jpg",
                         "images/vonNeumann/C01.jpg",  "images/vonNeumann/C10.jpg",
                         "images/vonNeumann/C11.jpg",  "images/vonNeumann/S000.jpg",
                         "images/vonNeumann/S00.jpg",  "images/vonNeumann/S01.jpg",
                         "images/vonNeumann/S0.jpg",   "images/vonNeumann/S10.jpg",
                         "images/vonNeumann/S11.jpg",  "images/vonNeumann/S1.jpg",
                         "images/vonNeumann/S.jpg",    "images/vonNeumann/T000.jpg",
                         "images/vonNeumann/T001.jpg", "images/vonNeumann/T010.jpg",
                         "images/vonNeumann/T011.jpg", "images/vonNeumann/T020.jpg",
                         "images/vonNeumann/T021.jpg", "images/vonNeumann/T030.jpg",
                         "images/vonNeumann/T031.jpg", "images/vonNeumann/T100.jpg",
                         "images/vonNeumann/T101.jpg", "images/vonNeumann/T110.jpg",
                         "images/vonNeumann/T111.jpg", "images/vonNeumann/T120.jpg",
                         "images/vonNeumann/T121.jpg", "images/vonNeumann/T130.jpg",
                         "images/vonNeumann/T131.jpg" ):
            img = None #pygame.image.load( imgFile ).convert()
            self.palette.append( img )


    ## Used to append cells to the list of cells to handle in the next step
    def enlist( self, x, y ):
        for i in ( ( (x)   + (y)*self.sizeX ),
                   ( (x+1) + (y)*self.sizeX ),
                   ( (x-1) + (y)*self.sizeX ),
                   ( (x) + (y-1)*self.sizeX ),
                   ( (x) + (y+1)*self.sizeX ) ):
            if self.cActArr[ i ] == False:
                self.cActArr[ i ] = True
                self.cList[self.cCounter] = i
                self.cCounter += 1

    def click_on_cell( self, x, y, mousekey, mods ):
        EPS = 128
        SPECIAL = 1024
        CSTATE = 2048
        SSTATE = 4096
        TSTATE = 6144

        if x <= 0 or x >= self.sizeX-1 or y <= 0 or y >= self.sizeY-1:
            return
        state = self.states[self.displayConf[x][y]]
        s = 0

        if e.button == 1:
            # T-states
            s = TSTATE
            if mods & pygame.KMOD_LCTRL:
                # eps
                if state & EPS == 0 and (state & TSTATE == TSTATE):
                    # to just insert a new eps without changing anything
                    self.currConf[x][y] = state+EPS
                    self.nextConf[x][y] = state+EPS
                    self.enlist(x,y)
                    return
                s += EPS
            if mods & pygame.KMOD_LSHIFT:
                # u
                s += SPECIAL
            if state == 0:
                for nbs in ( self.states[self.displayConf[x+1][y]],
                             self.states[self.displayConf[x][y-1]],
                             self.states[self.displayConf[x-1][y]],
                             self.states[self.displayConf[x][y+1]] ):
                    if ( nbs & TSTATE == TSTATE ) \
                            and ( ( mods & pygame.KMOD_LSHIFT == state & SPECIAL ) \
                                      and ( mods & pygame.KMOD_LCTRL == state & EPS ) ):
                        s += nbs & 768
                        self.currConf[x][y] = s
                        self.nextConf[x][y] = s
                        self.enlist(x,y)
                        return
            s += (((state&768)+256) & 768)
            self.currConf[x][y] = s
            self.nextConf[x][y] = s
            self.enlist(x,y)
        if e.button == 3:
            if mods & pygame.KMOD_LCTRL:
                # C-states
                s = CSTATE
                s += (((state&3)+1) & 3)
            elif mods & pygame.KMOD_LSHIFT:
                # S-states
                if state == 0 or (state & SSTATE) != SSTATE:
                    s = SSTATE
                    self.currConf[x][y] = s
                    self.nextConf[x][y] = s
                    self.enlist(x,y)
                    return
                sIdx = ( ( self.displayableStateDict[state] - 5 + 1 ) % 8 ) + 5
                s = self.states[sIdx]
            else:
                # U-state
                s = 0
            self.currConf[x][y] = s
            self.nextConf[x][y] = s
            self.enlist(x,y)

    def get_config( self ):
        for i in range( 1, self.sizeX-1 ):
            for j in range( 1, self.sizeY-1 ):
                if self.displayableStateDict.has_key( self.currConf[i][j] ):
                    self.displayConf[i][j] = self.displayableStateDict[self.currConf[i][j]]
                else:
                    print "Unkown state in cell", i, j, ":", self.currConf[i][j]
        return self.displayConf

    def importConf( self, filename ):
        with open( filename, 'r' ) as f:
            line = f.readline()
            while line[0:1] == "#":
                line = f.readline()
            if line[0:4] != "x = ":
                # fall back to familiar CASimulator/Xasim fileformat
                CA.importConf( self, filename )
            else:

                line = line[4:]
                sizeX = 0
                sizeX = int(line[0:line.find(",")])+2
                line = line[line.find("y = ")+4:]
                sizeY = 0
                sizeY = int(line[0:line.find(",")])+2
                line = line[line.find("rule = ")+7:]
                rule = line[:-1]

                if sizeX != self.sizeX or sizeY != self.sizeY:
                    self.resize( sizeX, sizeY )

                rleStateDict = { ".": "U",
                                 "A": "S",     "B": "S0",    "C": "S1",    "D": "S00",
                                 "E": "S01",   "F": "S10",   "G": "S11",   "H": "S000",
                                 "I": "T000",  "J": "T010",  "K": "T020",  "L": "T030",
                                 "M": "T001",  "N": "T011",  "O": "T021",  "P": "T031",
                                 "Q": "T100",  "R": "T110",  "S": "T120",  "T": "T130",
                                 "U": "T101",  "V": "T111",  "W": "T121",  "X": "T131",
                                 "pA": "C00",  "pB": "C01",  "pC": "C10",  "pD": "C11" }

# 63.8ILILILILIL$63.J.J.pA.pA.IJIJIJIJL$63.J.J.J.J9.IL$57.IL4IpAIpAIpAI
# pAIpAIpAIpAIpA.LK$57.JIJ3.L.L.2LKLKLKLKLK.IL$57.J5.L.L.LILILILILIL.LK
# .IL$57.J5.L.L.L.L.L.L.pA.pA.L2.JL$57.J5.16IL2.JL$57.J15.L6K2.JL$52.IL
# IL.J5.10ILILILILILJL$52.JLJL.J5.J.J.pA.pA.pA.IJIJLJLJLJL$52.JLJL.J.IL
# 2.J.J.J.J.J5.IJIJIJL$52.JLJL.J.J3IpAIpAIpAIpAIpAIpAIpA.L6K$52.JLJL.J.
# J3.L.L.L.L.L.2LK.IL$52.JLJL.J.J3.L.L.L.L.L.LIL.JL$52.JLJL.J.J3.L.L.L.
# L.L.2LK.JL$52.JLJL.J.J3.L.L.L.L.L.LIL.JLIL$52.JLJL.J.J3.L.L.L.pA.pA.p
# .L.JLJL$52.JLJL.J.J3.14IJIJ5IL$52.JLJLIpAIpA25IL$52.JIJI2J.J25.L$52.J


                # since RLE-configuration files don't imply ghostcells, they are added here!
                x = 1
                y = 1
                mx = 0
                importRegexp = re.compile( "((\d*)(\.|(p*)[A-X]))|(\$)|(\!)" )
                for line in f:
                    content = importRegexp.findall( line[0:-2] )
                    for c in content:
                        if c[0] != "":
                            if c[1] != "":
                                r = int(c[1])
                            else:
                                r = 1
                            for s in range(r):
                                self.currConf[x][y] = self.nameStateDict[rleStateDict[c[2]]]
                                x += 1
                        elif c[4] != "":
                            if x > mx:
                                mx = x
                            x = 1
                            y += 1
                        elif c[5] != "":
                            break

                self.nextConf = self.currConf.copy()
                f.close()

        # now, get all active cells:
        for x in range(1,self.sizeX-1):
            for y in range(1,self.sizeY-1):
                if self.currConf[x,y] in ( 2049, 2050, 2051, 4096, 4128, 4144, 4160,
                                           4168, 4176, 4184, 4192, 6272, 6528, 6784,
                                           7040, 7296, 7552, 7808, 8064 ):
                    self.enlist(x,y)


    def loopFunc( self ):
        self.step()

    def resize( self, sizeX, sizeY = None ):
        CA.resize( self, sizeX, sizeY )
        self.displayConf = np.zeros( self.size, int )
        self.cActArr = np.zeros( self.sizeX*self.sizeY, bool )
        self.nActArr = np.zeros( self.sizeX*self.sizeY, bool )
        self.cList = np.zeros( (self.sizeX*self.sizeY), int )
        self.nList = np.zeros( (self.sizeX*self.sizeY), int )

    def setConf( self, conf ):
        if conf.shape != self.currConf.shape:
            self.resize( conf[0].size, conf[1].size )
        for i in range( 1, self.sizeX-1 ):
            for j in range( 1, self.sizeY-1 ):
                self.currConf[i][j] = self.states[conf[i][j]]
                self.nextConf[i][j] = self.states[conf[i][j]]

    ## Calls the actual function that is used to calculate the next configuration
    def step( self ):
        self.updateAllCellsWeaveInlineFewStates()
#        self.updateAllCellsWeaveInline()

    ## Updates all cells using scipy.weave.inline
    def updateAllCellsWeaveInline( self ):
#
# All states are encoded in a bitmask:
#
#    <--MSB                     10                              LSB
#  ...... 0 0 0 0 0 0 0 0 0 X X u a1 a0 eps sc1 sc0 s2 s1 s0 e1 e0
#                           | | | |  |  |    |   |   |  |  |  |  |-> current e
#  XX = 00 -> U    <--------| | | |  |  |    |   |   |  |  |  |----> next e
#  XX = 01 -> C    <----------| | |  |  |    |   |   |  |  |
#  XX = 10 -> S                 | |  |  |    |   |   |  |  |-------> lsb on S
#  XX = 11 -> T                 | |  |  |    |   |   |  |----------> ...
#                               | |  |  |    |   |   |-------------> msb on S
#  S{} is encoded as SMASK_111  | |  |  |    |   |-----------------> s-state counter
#                               | |  |  |    |---------------------> s-state counter
#                               | |  |  |
#                               | |  |  |--------------------------> excited
#                               | |  |-----------------------------> direction
#                               | |--------------------------------> direction
#                               |----------------------------------> special
#
        vonNeumannCode = """
#include <stdlib.h>
#include <stdio.h>

#line 1 "CA.py"
#define UMASK          0
#define CMASK       2048  // 1 << 11
#define SMASK       4096  // 2 << 11
#define TMASK       6144  // 3 << 11
#define CSTATEMASK     3  // 1|2
#define SSTATEMASK    28  // 4|8|16
#define TSTATEMASK  1920  // 128|256|512|1024
#define e0     1
#define e1     2
#define s0     4
#define s1     8
#define s2    16
#define s     28  // s2|s1|s0
#define sc0   32
#define sc1   64
#define sc    96  // sc1|sc0
#define eps  128
#define a0   256
#define a1   512
#define a    768  // a1|a0
#define u   1024

#define U(x) ((x) == 0)
#define C(x) (((x) & CMASK) == CMASK)
#define S(x) (((x) & SMASK) == SMASK)
#define T(x) (((x) & TMASK) == TMASK)

#define A_UNSHIFT(x)  (((x)&a)>>8)
#define SC_SHIFT(x)   ((x)<<5)
#define SC_UNSHIFT(x) (((x)&sc)>>5)

  int i, j, k, l;
  int nbs[4];
  int state;
  for ( i = 1; i < sizeX-1; i++ ) {
    for ( j = 1; j < sizeY-1; j++ ) {
      state = cconf( i, j );
      nbs[0] = cconf( i+1, j );
      nbs[1] = cconf( i, j-1 );
      nbs[2] = cconf( i-1, j );
      nbs[3] = cconf( i, j+1 );

      if ( T(state) ) { // transmission state
        // transisition rule (T.1):
        for ( k = 0; k < 4; k++ ) {
          if ( T(nbs[k]) && ( abs(k-(A_UNSHIFT(nbs[k]))) == 2)
               && ((nbs[k]&u) != (state&u)) && (nbs[k]&eps)  ) {
            // (T.1)(alpha)
            nconf( i, j ) = UMASK;
            break;
          }
        }
        if ( k < 4 ) continue;

        // (T.1)(beta)
        for ( k = 0; k < 4; k++ ) {
          if ( T(nbs[k]) && (abs((A_UNSHIFT(nbs[k]))-(A_UNSHIFT(state))) != 2)
               && (abs(k-(A_UNSHIFT(nbs[k]))) == 2)
               && ((nbs[k]&u) == (state&u) ) && (nbs[k]&eps) ) {
            // (T.1)(beta)(a)
            nconf( i, j ) = state | eps;
            break;
          }
          if ( C(nbs[k]) && (nbs[k]&e0) && (k-(A_UNSHIFT(state)) != 0) ) {
            // (T.1)(beta)(b)
            nconf( i, j ) = state | eps;
            break;
          }
        }

        if ( k < 4 ) continue;

        // (T.1)(gamma)
        nconf( i, j ) = TMASK | (state&u) | (state&a);
      } // end of T(state)


      else if ( C(state) ) { // confluent state
        // transistion rule (T.2)
        for ( k = 0; k < 4; k++ ) {
          if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2)
               && (nbs[k]&eps) && (nbs[k]&u) ) {
            // (T.2)(alpha)
            nconf( i, j ) = UMASK;
            break;
          }
        }
        if ( k < 4 ) continue;

        // (T.2)(beta)
        for( k = 0; k < 4; k++ ) {
          if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2)
               && (nbs[k]&eps) && !(nbs[k]&u) ) {
            // (T.2)(beta)(a)
            break;
          }
        }
        if ( k < 4 ) {
          for ( k = 0; k < 4; k++ ) {
            if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2)
                 && !(nbs[k]&eps) && !(nbs[k]&u) ) {
              // (T.2)(beta)(b)
              break;
            }
          }
          if ( k == 4 ) {
            nconf( i, j ) = CMASK | e1 | ((state&e1)>>1);
            continue;
          }
        }

        // (T.2)(gamma)
        nconf( i, j ) = CMASK | ((state&e1)>>1);
      } // end of C(state)

      else if ( U(state) ) {  // unexcitable state
        // transition rule (T.3)
        for ( k = 0; k < 4; k++ ) {
          if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
            // (T.3)(alpha)
            nconf( i, j ) = SMASK;
            break;
          }
        }
        // (T.3)(beta)
        // doesn' change the state
      } // end of U(state)

      else if ( S(state) ) { // sensitized state
        if ( !(state&sc1)  ) {
          // transition rule (T.4)
          for ( k = 0; k < 4; k++ ) {
            if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
              // (T.4)(alpha)
              nconf( i, j ) = state | (s0<<(2-SC_UNSHIFT(state)));
              break;
            }
          }
          // (T.4)(beta)
          // doesn't change the state but the counter
          nconf( i, j ) += sc0;
        } else {
          if ( (state&sc) == sc ) {
            for ( k = 0; k < 4; k++ ) {
              if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
                nconf( i, j ) = TMASK | a0;
                break;
              }
            }
            if ( k == 4 ) {
              nconf( i, j ) = TMASK;
            }
          } else {
            for ( k = 0; k < 4; k++ ) {
              if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
                nconf( i, j ) = state | s0;
                break;
              }
            }
            nconf( i, j ) += sc0;

            if ( nconf( i, j ) & s ) {
              // make transition from sensitized to transmission or confluent state
              l = nconf( i, j );
              if ( (l & s) == s ) {
                nconf( i, j ) = CMASK;
              } else {
                // other leaves of the S-to-T-transition tree of depth 3
                l += s0;
                nconf( i, j ) = TMASK | ((l&s)<<6);
              }
            }
          }// else {
            // stay for another run
        //}
        }
      }

      else  {
    // this state is undefined!
      }
    }
  }
"""

        cconf = self.currConf
        nconf = self.nextConf
        sizeX = self.sizeX
        sizeY = self.sizeY
        weave.inline( vonNeumannCode, [ 'cconf', 'nconf', 'sizeX', 'sizeY' ],
                      type_converters = converters.blitz,
                      compiler = 'gcc' )
        self.currConf = self.nextConf.copy()


    ## Update cells, but only those that changed or are in the neighbourhood of one of those.
    # This is done via bitchecking, and hence admittedly difficult to read.
    # Every subsection of the transitionfunction from von Neumann's paper is marked.
    def updateAllCellsWeaveInlineFewStates( self ):
#
# All states are encoded in a bitmask:
#
#    <--MSB                     10                              LSB
#  ...... 0 0 0 0 0 0 0 0 0 X X u a1 a0 eps sc1 sc0 s2 s1 s0 e1 e0
#                           | | | |  |  |    |   |   |  |  |  |  |-> current e
#  XX = 00 -> U    <--------| | | |  |  |    |   |   |  |  |  |----> next e
#  XX = 01 -> C    <----------| | |  |  |    |   |   |  |  |
#  XX = 10 -> S                 | |  |  |    |   |   |  |  |-------> lsb on S
#  XX = 11 -> T                 | |  |  |    |   |   |  |----------> ...
#                               | |  |  |    |   |   |-------------> msb on S
#  S{} is encoded as SMASK_111  | |  |  |    |   |-----------------> s-state counter
#                               | |  |  |    |---------------------> s-state counter
#                               | |  |  |
#                               | |  |  |--------------------------> excited
#                               | |  |-----------------------------> direction
#                               | |--------------------------------> direction
#                               |----------------------------------> special
#
#
        vonNeumannCodeFewStates = """
#include <stdlib.h>
#include <stdio.h>

#line 1 "VonNeumannDefinesInCA.py"
#define UMASK          0
#define CMASK       2048  // 1 << 11
#define SMASK       4096  // 2 << 11
#define TMASK       6144  // 3 << 11
#define CSTATEMASK     3  // 1|2
#define SSTATEMASK    28  // 4|8|16
#define TSTATEMASK  1920  // 128|256|512|1024
#define e0     1
#define e1     2
#define s0     4
#define s1     8
#define s2    16
#define s     28  // s2|s1|s0
#define sc0   32
#define sc1   64
#define sc    96  // sc1|sc0
#define eps  128
#define a0   256
#define a1   512
#define a    768  // a1|a0
#define u   1024

/* checkers for different kinds of states */
#define U(x) ((x) == 0)
#define C(x) (((x) & CMASK) == CMASK)
#define S(x) (((x) & SMASK) == SMASK)
#define T(x) (((x) & TMASK) == TMASK)

/* get the direction of a T-state and the 'age' of an S-state */
#define A_UNSHIFT(x)  (((x)&a)>>8)
#define SC_SHIFT(x)   ((x)<<5)
#define SC_UNSHIFT(x) (((x)&sc)>>5)

/* enlist a cell to be checked in the next step */
#define ENLIST(id) if ( !nActArr( (id) ) ) {\
                     nActArr( id ) = true;\
                     nList( nCounter++ ) = id;\
                   }

/* enlist a cell and it's neighbourhood to be checke in the next step */
#define MARKNBH(x,y) ENLIST( (x)+(y)*sizeX );\
                     ENLIST( (x+1)+(y)*sizeX );\
                     ENLIST( (x-1)+(y)*sizeX );\
                     ENLIST( (x)+(y-1)*sizeX );\
                     ENLIST( (x)+(y+1)*sizeX );


#include <stdio.h>
#line 1 "VonNeumannCodeInCA.py"
int i, j, k, l, x, y, aa;

/* the neighbours' states */
int nbs[4];
/* the 'own' state */
int state;
/* the number of cells that have to be checked in the next step and is returned as return_val */
int nCounter = 0;
for ( i = 0; i < cCounter; i++ ) {
  x = cList( i ) % sizeX;
  y = cList( i ) / sizeX;
  cActArr( cList( i ) ) = false;

  state = cconf( x, y );
  nbs[0] = cconf( x+1, y );
  nbs[1] = cconf( x, y-1 );
  nbs[2] = cconf( x-1, y );
  nbs[3] = cconf( x, y+1 );

  if ( T(state) ) { // transmission state
    // transisition rule (T.1):
    for ( k = 0; k < 4; k++ ) {
      if ( T(nbs[k]) && ( abs(k-(A_UNSHIFT(nbs[k]))) == 2)
           && ((nbs[k]&u) != (state&u)) && (nbs[k]&eps)  ) {
        // (T.1)(alpha)
        nconf( x, y ) = UMASK;
        break;
      }
    }
    if ( k < 4 ) continue;

    // (T.1)(beta)
    for ( k = 0; k < 4; k++ ) {
      if ( T(nbs[k]) && (abs((A_UNSHIFT(nbs[k]))-(A_UNSHIFT(state))) != 2)
           && (abs(k-(A_UNSHIFT(nbs[k]))) == 2)
           && ((nbs[k]&u) == (state&u) ) && (nbs[k]&eps) ) {
        // (T.1)(beta)(a)
        nconf( x, y ) = state | eps;
        MARKNBH( x, y );
        break;
      }
      if ( C(nbs[k]) && (nbs[k]&e0) && (k-(A_UNSHIFT(state)) != 0) ) {
        // (T.1)(beta)(b)
        nconf( x, y ) = state | eps;
        MARKNBH( x, y );
        break;
      }
    }

    if ( k < 4 ) continue;

    // (T.1)(gamma)
    // don't enlist, since cell is not active
    // MARKNBH( x, y );
    nconf( x, y ) = TMASK | (state&u) | (state&a);
  } // end of T(state)


  else if ( C(state) ) { // confluent state
    // transistion rule (T.2)
    for ( k = 0; k < 4; k++ ) {
      if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2)
           && (nbs[k]&eps) && (nbs[k]&u) ) {
        // (T.2)(alpha)
        // don't enlist, since cell is not active
        nconf( x, y ) = UMASK;
        break;
      }
    }
    if ( k < 4 ) continue;

    // (T.2)(beta)
    for( k = 0; k < 4; k++ ) {
      if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2)
           && (nbs[k]&eps) && !(nbs[k]&u) ) {
        // (T.2)(beta)(a)
        MARKNBH( x, y );
        break;
      }
    }
    if ( k < 4 ) {
      for ( k = 0; k < 4; k++ ) {
        if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2)
             && !(nbs[k]&eps) && !(nbs[k]&u) ) {
          // (T.2)(beta)(b)
          MARKNBH( x, y );
          break;
        }
      }
      if ( k == 4 ) {
        nconf( x, y ) = CMASK | e1 | ((state&e1)>>1);
        MARKNBH( x, y );
        continue;
      }
    }

    // (T.2)(gamma)
    nconf( x, y ) = CMASK | ((state&e1)>>1);
    MARKNBH( x, y );
  } // end of C(state)

  else if ( U(state) ) {  // unexcitable state
    // transition rule (T.3)
    for ( k = 0; k < 4; k++ ) {
      if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
        // (T.3)(alpha)
        nconf( x, y ) = SMASK;
        MARKNBH( x, y );
        break;
      }
    }
    // (T.3)(beta)
    // doesn' change the state
  } // end of U(state)

  else if ( S(state) ) { // sensitized state
    MARKNBH( x, y );
    if ( !(state&sc1)  ) {
      // transition rule (T.4)
      for ( k = 0; k < 4; k++ ) {
        if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
          // (T.4)(alpha)
          nconf( x, y ) = state | (s0<<(2-SC_UNSHIFT(state)));
          break;
        }
      }
      // (T.4)(beta)
      // doesn't change the state but the counter
      nconf( x, y ) += sc0;
    } else {
      if ( (state&sc) == sc ) {
        for ( k = 0; k < 4; k++ ) {
          if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
            nconf( x, y ) = TMASK | a0;
            break;
          }
        }
        if ( k == 4 ) {
          nconf( x, y ) = TMASK;
        }
      } else {
        for ( k = 0; k < 4; k++ ) {
          if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
            nconf( x, y ) = state | s0;
            break;
          }
        }
        nconf( x, y ) += sc0;

        if ( nconf( x, y ) & s ) {
          // make transition from sensitized to transmission or confluent state
          l = nconf( x, y );
          if ( (l & s) == s ) {
            nconf( x, y ) = CMASK;
          } else {
            // other leaves of the S-to-T-transition tree of depth 3
            l += s0;
            nconf( x, y ) = TMASK | ((l&s)<<6);
          }
        }
      }// else {
      // stay for another run
      //}
    }
  }

  else  {
    // this state is undefined!
  }
}
return_val = nCounter;
"""
        cconf = self.currConf
        nconf = self.nextConf
        sizeX = self.sizeX
        sizeY = self.sizeY
        cCounter = self.cCounter
        cList = self.cList
        nList = self.nList
        cActArr = self.cActArr
        nActArr = self.nActArr
        print "IN PY-1: cCounter", cCounter

        self.cCounter = weave.inline( vonNeumannCodeFewStates, [ 'cconf', 'nconf', 'sizeX', 'sizeY',
                                                                 'cList', 'nList', 'cCounter',
                                                                 'cActArr', 'nActArr' ],
                                      type_converters = converters.blitz,
                                      compiler = 'gcc' )
        self.currConf = self.nextConf.copy()
        self.cActArr, self.nActArr = self.nActArr.copy(), self.cActArr.copy()
        self.cList = self.nList

if __name__ == "__main__":
    import sys
    print sys.argv
    sizeX, sizeY = int(sys.argv[1]), 1
    ca = binRule(110, sizeX, sizeY, binRule.INIT_RAND)
    print "ca created"
    for i in range(int(sys.argv[2])):
        ca.loopFunc()
