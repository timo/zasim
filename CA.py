#!/usr/bin/python

import numpy as np
import pygame
import random
import sys
import os
import re
from multiprocessing import Array
import scipy
from scipy import weave
from scipy.weave import converters

# for catPile
from scipy.misc.pilutil import *
import Image

class CA():

    # init-codes
    INIT_ZERO = 0
    INIT_ONES = 1
    INIT_RAND = 2
    INIT_FILE = 3

    # flags to return after importing conf from file
    IMPORTOK = 0
    SIZECHANGED = 1
    WRONGCA = 2
    IMPORTNOTOK = 3

    palette = []
    
    def __init__( self ):
        print "function __init__() not implemented yet"

    def eventFunc( self, event ):
        print "function eventFunc() for", self.getTitle(), "not implemented yet"

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

    def exportConfAnnotatedLines( self, filename ):
        #### WERE USING XASIM-EXPORT-STYLE ####
        # don't use this function but exportConf()

        # for input/output of confs see
        # http://www.scipy.org/Cookbook/InputOutput

        # exporting conf to file in ascii-representation
        # rules:
        # - comments must not start with an '#'
        # - a new line with info about the conf starts with '#'
        # - a new line of the conf starts with '##'
        # - the last line that is going to be interpreted starts with '###'
            with open( filename, 'w' ) as f:
                # info
                f.write( "#title=" + self.getTitle() + "\n" )
                f.write( "#sizeX=" + str(self.sizeX) + "\n" )
                dim = self.getDim()
                if dim > 1:
                    f.write( "#sizeY=" + str(self.sizeY) + "\n" )
                f.write( "##Conf=\n" )
                # the conf
                if dim == 1:
                    f.write( "## " )
                    for i in range(self.sizeX):
                        f.write( str(self.currConf[i,0]) + " " )
                    f.write( "\n" )
                elif dim == 2:
                    for j in range(self.sizeY):
                        f.write( "## " )
                        for i in range(self.sizeX):
                            f.write( str(self.currConf[i][j]) + " " )
                        f.write( "\n" )
                # end-tag
                f.write( "###\n" )
                f.close()

    def getType( self ):
        return self.title.upper()

    def getConf( self ):
        return self.currConf
    
    def getDim( self ):
        return self.dim

    def getSize( self ):
        return self.size
    
    def getTitle( self ):
        return self.title
    
    def importConf( self, filename ):
        retVal = self.IMPORTOK
        with open( filename, 'r' ) as f:
            # sizeX
            sizeX = f.readline()
            # remove "\n" at end of line
            sizeX = int(sizeX[0:-1])

            if self.getDim() > 1:
                # sizeY
                sizeY = f.readline()
                # remove "\n" at end of line
                sizeY = sizeY[0:-1]
                # check 
                if not sizeY.isdigit():
                    print "ERROR importing conf!"
                    return
                sizeY = int(sizeY)
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
                    if content[1] == '':
                        print "error importing file"
                        sys.exit()
                    state = int(content[1])
                    self.currConf[i][j] = state
                    self.nextConf[i][j] = state
            f.close()
        return retVal


    def importConfAnnotatedLines( self, filename ):
        #### WERE USING XASIM-EXPORT-STYLE ####
        # don't use this function but importConf()
        
            with open( filename, 'r' ) as f:
                for line in f:
                    line = line[0:-1]
                    # read info
                    if line[0:7] == "#title=":
                        title = line[7:]
                    elif line[0:7] == "#sizeX=":
                        sizeX = int(line[7:])
                    elif line[0:7] == "#sizeY=":
                        sizeY = int(line[7:])
                    elif line[0:12] == "#stepsTaken=":
                        if line[12:] == "n/a":
                            steps = 0
                        else:
                            steps = int(line[15:])
                    elif line[0:] == "##Conf=":
                        # now import conf, but make some checks first
                        break;

                retVal = self.IMPORTOK

                if title != self.getTitle():
                    print "TODO: opening different kind of ca-conf!!"
                    f.close()
                    return self.WRONGCA

                dim = self.getDim()
                if dim == 1:
                    sizeY = 1
                    if sizeX != self.sizeX:
                        retVal = self.SIZECHANGED
                        self.resize( sizeX )
                elif dim == 2:
                    if sizeX != self.sizeX or sizeY != self.sizeY:
                        retVal = self.SIZECHANGED
                        self.resize( sizeX, sizeY )
                    
                # y: counter of imported lines (checking!)
                y = 0
                for line in f:
                    line = line[0:-1]
                    if line[0:3] == "###":
                        if y != sizeY:
                            f.close()
                            return self.IMPORTNOTOK
                        break
                    elif line[0:3] == "## ":
                        # thats a conf-line!
                        line = line[3:]
                        s = line
                        x = 0
                        while x < sizeX:
                            s = s.partition( " " )
                            if dim == 1:
                                self.currConf[x,0] = int(s[0])
                            elif dim == 2:
                                self.currConf[x,y] = int(s[0])
                            s = s[2]
                            x += 1
                    y += 1
            f.close()
            return retVal


    def loopFunc( self ):
        print "function loopFunc() not implemented yet"

    def quit( self ):
        print "function quit() not implemented yet"
    
    def resize( self, sizeX, sizeY = None ):
        self.sizeX = sizeX
        if sizeY == None:
            sizeY = self.sizeY
        else:
            self.sizeY = sizeY
        self.size = sizeX,sizeY
        if self.getDim() == 1:
            self.currConf = np.zeros( (sizeX,1), int )
            self.nextConf = np.zeros( (sizeX,1), int )
        elif self.getDim() == 2:
            self.currConf = np.zeros( self.size, int )
            self.nextConf = np.zeros( self.size, int )
        
    def setConf( self, conf ):
        self.currConf = conf.copy()
        self.nextConf = conf.copy()


########## binrule ##############
class binRule( CA ):
    palette = [ (0,0,0), (255,255,255) ]

    def __init__ ( self, ruleNr, sizeX, sizeY, initConf, filename="" ):
        self.dim = 1
        if not 0 <= ruleNr < 256:
            print "binRule only supports ruleNr between 0 and 255!"
            sys.exit(1)

        self.ruleNr = ruleNr
        self.sizeX = sizeX
        self.sizeY = sizeY
        self.size = ( sizeX, sizeY )
        self.title = "Rule" + str( self.ruleNr )

        if initConf == self.INIT_ZERO:
            self.currConf = np.zeros( (sizeX, 1), int )
            self.nextConf = np.zeros( (sizeX, 1), int )
        elif initConf == self.INIT_ONES:
            self.currConf = np.ones( (sizeX, 1), int )
            self.nextConf = np.ones( (sizeX, 1), int )
        elif initConf == self.INIT_RAND:
            self.currConf = np.zeros( (sizeX, 1), int )
            self.nextConf = np.zeros( (sizeX, 1), int )
            for i in range( sizeX ):
                self.currConf[i,0] = random.randint( 0, 1 )
            self.nextConf = self.currConf.copy()
        else:
            print "The initflag you've provided isn't available for the binRule-CA"
            print "Available initflags:"
            print "INIT_ZERO, INIT_ONES, INIT_RAND, INIT_FILE + filename"
            sys.exit(1)
        
        if filename != "":
            self.importConf( filename )

        # init the rule
        self.ruleIdx = np.zeros( 8, int )
        for i in range( 8 ):
            if ( self.ruleNr & ( 1 << i ) ):
                self.ruleIdx[i] = 1

    def getType( self ):
        return self.title.upper() + str(self.ruleNr)

    def loopFunc( self ):
        self.step()

    def quit( self ):
        pass
    
    def step( self ):
        self.updateAllCellsWeaveInline()

    def updateAllCellsPy( self ):
        for i in range( 1, self.sizeX-1 ):
            state =  self.currConf[i-1] << 2
            state += self.currConf[i] << 1
            state += self.currConf[i+1]
            self.nextConf[i] = self.ruleIdx[state]
        self.currConf, self.nextConf = self.nextConf, self.currConf

    def updateAllCellsWeaveInline( self ):
        binRuleCode = """
#include <stdio.h>
#line 1 "CA.py"
int i;
int state;
for ( i = 1; i < sizeX-1; i++ ) {
  state =  cconf(i-1,0) << 2;
  state += cconf(i  ,0) << 1;
  state += cconf(i+1,0);
  nconf(i,0) = rule(state);
}
nconf(0,0) = nconf(sizeX-2,0);
nconf(sizeX-1,0) = nconf(1,0);
"""
        cconf = self.currConf
        nconf = self.nextConf
        sizeX = self.sizeX
        rule = self.ruleIdx
        weave.inline( binRuleCode, ['cconf', 'nconf', 'sizeX', 'rule'],
                      type_converters = converters.blitz,
                      compiler = 'gcc' )
        self.currConf = self.nextConf.copy()



class ballRule( binRule ):
    palette=[]
    def __init__( self, ruleNr, sizeX, sizeY, initConf, filename="" ):
        binRule.__init__( self, ruleNr, sizeX, sizeY, initConf, filename="" )
        self.title = "ballRule"

        pygame.init()
        pygame.display.set_mode( (sizeX,sizeY), 0, 8 )
        
        palette = []
        for filename in ( "images/balls/ball_red.png" , "images/balls/ball_blue.png" ): 
            img = pygame.image.load( filename ).convert()
            self.palette.append( img )



########## sandPile #############
class sandPile( CA ):
    # currConf is the current state
    # nextConf is the next step after the current
    
    black = 0,0,0
    white = 255,255,255
    red = 255,0,0
    green = 0,255,0
    blue = 0,0,255
    grey = 170,170,170
    pink = 250,40,230
    darkred = 95,0,16
    yellow = 255,240,0
    
#    palette = [blue, white, yellow, darkred, grey, pink, green, red]
    palette = [(0, 0, 0), (32, 32, 32), (64, 64, 64), (96, 96, 96), 
               (128, 128, 128), (160, 160, 160), (192, 192, 192), (224, 224, 224)]

    
    info = ( "state 0", "state 1", "state 2", "state 3", 
             "state 4", "state 5", "state 6", "state 7" )
    
    def __init__( self, sizeX, sizeY, initConf, filename="" ):
        self.dim = 2
        self.title = "Sandpile"
        self.size = self.sizeX,self.sizeY = sizeX,sizeY

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
            print "The initflag you've provided isn't available for the sandPile-CA"
            print "Available initflags:"
            print "INIT_ZERO, INIT_RAND, INIT_FILE + filename"
            sys.exit(1)

        if filename != "":
            self.importConf( filename )
            
    def addGrain( self, x, y ):
        if not ( (x > self.sizeX - 1) or (y > self.sizeY - 1) ):
            if self.currConf[ x, y ] < 7:
                self.currConf[ x, y ] += 1

    def addGrainRandomly( self ):
        x = random.randint( 1, self.sizeX-1 )
        y = random.randint( 1, self.sizeY-1 )
        while self.currConf[ x, y ] >= 7:
            x = random.randint( 1, self.sizeX-1 )
            y = random.randint( 1, self.sizeY-1 )
        self.currConf[ x, y ] += 1

    def eventFunc( self, e ):
        if e.type == pygame.MOUSEBUTTONDOWN:
            x,y = e.pos
            if e.button == 1:
                self.addGrain( x, y )
            if e.button == 3:
                self.setState( x, y, 0 )
        
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

    def setState( self, x, y, s ):
        if 0 <= s < 8 and 0 < x < (self.sizeX-1) and 0 < y < (self.sizeY-1):
            self.currConf[ x, y ] = s
            self.nextConf[ x, y ] = s
    
    def step( self ):
        self.updateAllCellsWeaveInline()

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
        




########## catPile #############
class catPile( sandPile ):

    def __init__( self, sizeX, sizeY, initConf ):
        self.readImage( "cat.jpg" )
            
    def readImage( self, filename ):
        dummy_data = Image.open(filename)
        dummy_data = dummy_data.convert("I")
        
        image = fromimage(dummy_data)
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


######### ballPile ##########
class ballPile( sandPile ):
    palette=[]
    def __init__( self, sizeX, sizeY, initConf, filename="" ):
        sandPile.__init__( self, sizeX, sizeY, initConf, filename ) 

        pygame.init()
        pygame.display.set_mode( (sizeX,sizeY), 0, 8 )

        self.palette = []
        for filename in ( 
            "images/balls/ball_black.png", "images/balls/ball_red.png" , 
            "images/balls/ball_blue.png" , "images/balls/ball_orange.png",
            "images/balls/ball_green.png", "images/balls/ball_pink.png" , 
            "images/balls/ball_grey.png" , "images/balls/ball_white.png" ):
            img = pygame.image.load( filename ).convert()
            self.palette.append( img )

    def getTitle( self ):
        return "BallPile"


########## von Neumann ##########
class vonNeumann ( CA ):
    palette = []
    
    def __init__( self, sizeX, sizeY, confFile ):
        self.title = "vonNeumann"
        self.dim = 2
        self.size = self.sizeX, self.sizeY = sizeX, sizeY
        
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
        
        self.nameStateDict = { "U": 0,
                               "C00" : 2048, "C10" : 2049, "C01" : 2050, "C11" : 2051,
                               "S000": 4192, "S00" : 4160, "S01" : 4168, "S0"  : 4128,
                               "S10" : 4176, "S11" : 4184, "S1"  : 4144, "S"   : 4096,
                               "T000": 6144, "T001": 6272, "T010": 6400, "T011": 6528, 
                               "T020": 6656, "T032": 6784, "T030": 6912, "T031": 7040, 
                               "T100": 7168, "T101": 7296, "T110": 7424, "T111": 7552,
                               "T120": 7680, "T121": 7808, "T130": 7936, "T131": 8064 }

        self.states = [ 0, 2048, 2049, 2050, 2051, 4192, 4160, 4168, 4128, 4176, 
                        4184, 4144, 4096, 6144, 6272, 6400, 6528, 6656, 6784, 
                        6912, 7040, 7168, 7296, 7424, 7552, 7680, 7808, 7936, 8064 ]

        # as usual, these two arrays contain the real configuration, that is used
        # in every step ...
        self.currConf = np.zeros( (sizeX, sizeY), int )
        self.nextConf = np.zeros( (sizeX, sizeY), int )
        if confFile != "":
            self.importConf( confFile )
            self.nextConf = self.currConf.copy()
        # ... but in this CA the states are not enumerable from 0..28, but scattered 
        # between 0..~2^13, so we need a dict (see below) to map the states to 0..28, 
        # so the Display-module can display states without knowing the difference
        self.displayConf = np.zeros( self.size, int)
 
        # used when updating only some cells instead of all....
        # BIG TODO!
        # self.cActArray = np.zeros( (sizeX*sizeY), bool )
        # self.nActArray = np.zeros( (sizeX*sizeY), bool )
        
        pygame.init()
        pygame.display.set_mode( self.size, 0, 8 )

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
            img = pygame.image.load( imgFile ).convert()
            self.palette.append( img )



    def enlist( self, x, y ):
        pass
        # self.cActArray[x*y] = True

    def eventFunc( self, e ):
        if e.type == pygame.MOUSEBUTTONDOWN:
            x,y = e.pos
            state = self.states[self.displayConf[x][y]]
            mods = pygame.key.get_mods()
            s = 0
            if e.button == 1:
                # T-states
                s = 6144
                if mods & pygame.KMOD_LCTRL:
                    # eps
                    if state & 128 == 0 and (state & 6144 == 6144):
                        # to just insert a new eps without changing anything
                        self.currConf[x][y] = state+128
                        self.nextConf[x][y] = state+128
                        self.enlist(x,y)
                        return
                    s += 128
                if mods & pygame.KMOD_LSHIFT:
                    # u
                    s += 1024
                if state == 0:
                    for nbs in ( self.states[self.displayConf[x+1][y]],
                                 self.states[self.displayConf[x][y-1]],
                                 self.states[self.displayConf[x-1][y]],
                                 self.states[self.displayConf[x][y+1]] ):
                        if ( nbs & 6144 == 6144 ) \
                                and ( ( mods & pygame.KMOD_LSHIFT == state & 1024 ) \
                                          and ( mods & pygame.KMOD_LCTRL == state & 128 ) ):
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
                    s = 2048
                    s += (((state&3)+1) & 3)
                elif mods & pygame.KMOD_LSHIFT:
                    # S-states
                    s = 4192
                    if (state & 4096) != 0:
                        s += (((state&28)+4) & 28)
                else:
                    # U-state
                    s = 0
                self.currConf[x][y] = s
                self.nextConf[x][y] = s
                self.enlist(x,y)

    def getConf( self ):
        for i in range( 1, self.sizeX-1 ):
            for j in range( 1, self.sizeY-1 ):
                if self.displayableStateDict.has_key( self.currConf[i][j] ):
                    self.displayConf[i][j] = self.displayableStateDict[self.currConf[i][j]]
                else:
                    print i, j, ":", self.currConf[i][j]
        return self.displayConf

    def importConf( self, filename ):
        with open( filename, 'r' ) as f:
            line = f.readline()
            while line[0:1] == "#":
                line = f.readline()
            if line[0:4] != "x = ":
                # fall back to familiar CASimulator/Xasim fileformat
                CA.importConf( self, filename )
                return

            line = line[4:]
            sizeX = 0
            sizeX = int(line[0:line.find(",")])
            line = line[line.find("y = ")+4:]
            sizeY = 0
            sizeY = int(line[0:line.find(",")])
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

            x = 0
            y = 0
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
                        x = 0
                        y += 1
                    elif c[5] != "":
                        break

            self.nextConf = self.currConf.copy()

            f.close()

    def loopFunc( self ):
        self.step()

    def resize( self, sizeX, sizeY = None ):
        CA.resize( self, sizeX, sizeY )
        self.displayConf = np.zeros( self.size, int )

    def setConf( self, conf ):
        if conf.shape != self.currConf.shape:
            self.resize( conf[0].size, conf[1].size )
        for i in range( 1, self.sizeX-1 ):
            for j in range( 1, self.sizeY-1 ):
                self.currConf[i][j] = self.states[conf[i][j]]
        
    def step( self ):
        self.updateAllCellsWeaveInline()

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

#define ADDTONLIST(x,y) nActArr((x)*(y)) = true;\
                        nActArr((x+1)*(y)) = true;\
                        nActArr((x)*(y-1)) = true;\
                        nActArr((x-1)*(y)) = true;\
                        nActArr((x)*(y+1)) = true;

  int g, h, i, j, k, l;
  int nbs[4];
  int state;
  h = 1;
  #include <stdio.h>
  for ( g = sizeX+1; g < sizeX*sizeY-sizeX; g++ ) {
    if ( !cActArr(g) )
      continue;

    cActArr(g) = false;
    i = g%sizeX;
    j = g/sizeX;
    printf(\"lala\");
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
          ADDTONLIST(i,j);
          break;
        }
        if ( C(nbs[k]) && (nbs[k]&e0) && (k-(A_UNSHIFT(state)) != 0) ) {
          // (T.1)(beta)(b)
          nconf( i, j ) = state | eps;
          ADDTONLIST(i,j);
          break;
        }
      }
      
      if ( k < 4 ) continue;

      // (T.1)(gamma)
      nconf( i, j ) = TMASK | (state&u) | (state&a);
      ADDTONLIST(i,j);
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
          ADDTONLIST(i,j);
          continue;
        }
      }

      // (T.2)(gamma)
      nconf( i, j ) = CMASK | ((state&e1)>>1);
      ADDTONLIST(i,j);
    } // end of C(state)

    else if ( U(state) ) {  // unexcitable state
      // transition rule (T.3)
      for ( k = 0; k < 4; k++ ) {
        if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
          // (T.3)(alpha)
          nconf( i, j ) = SMASK;
          ADDTONLIST(i,j);
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
            ADDTONLIST(i,j);
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
              ADDTONLIST(i,j);
              break;
            }
          }
          if ( k == 4 ) {
            nconf( i, j ) = TMASK;
            ADDTONLIST(i,j);
          }
        } else {
          for ( k = 0; k < 4; k++ ) {
            if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
              nconf( i, j ) = state | s0;
              ADDTONLIST(i,j);
              break;
            }
          }
          nconf( i, j ) += sc0;
          ADDTONLIST(i,j);

          if ( nconf( i, j ) & s ) {
            // make transition from sensitized to transmission or confluent state
            l = nconf( i, j );
            if ( (l & s) == s ) {
              nconf( i, j ) = CMASK;
              ADDTONLIST(i,j);
            } else {
              // other leaves of the S-to-T-transition tree of depth 3
              l += s0;
              nconf( i, j ) = TMASK | ((l&s)<<6);
              ADDTONLIST(i,j);
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

"""

        cconf = self.currConf
        nconf = self.nextConf
        sizeX = self.sizeX
        sizeY = self.sizeY
        cActArr = self.cActArray
        nActArr = self.nActArray
        weave.inline( vonNeumannCode, [ 'cconf', 'nconf', 'sizeX', 'sizeY', 
                                        'cActArr', 'nActArr' ],
                      type_converters = converters.blitz,
                      compiler = 'gcc' )
        self.currConf = self.nextConf.copy()
        self.cActArray,self.nActArray = self.nActArray,self.cActArray

if __name__ == "__main__":
    sizeX, sizeY = 10, 10
    pygame.init()
    screen = pygame.display.set_mode( (sizeX,sizeY), 0, 8 )
    surf = pygame.surface.Surface( (sizeX, sizeY ), 0, 8 )
    ca = ballPile( 10, 10 )
