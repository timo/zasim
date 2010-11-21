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
        print "function eventFunc() not implemented yet"

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

    def getConf( self ):
        return self.currConf
    
    def getDim( self ):
        return 0

    def getSize( self ):
        return self.size
    
    def getTitle( self ):
        return ""
    
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
                
            importRegexp = re.compile("\((\d)\)")
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
        if conf.size != self.currConf.size:
            if self.getDim() == 1:
                self.resize( conf[0].size )
            elif self.getDim() == 2:
                self.resize( conf[0].size, conf[1].size )
        self.currConf = conf.copy()
        self.nextConf = conf.copy()


########## binrule ##############
class binRule( CA ):
    palette = [ (0,0,0), (255,255,255) ]

    def __init__ ( self, ruleNr, sizeX, sizeY, initConf, filename="" ):

        if not 0 <= ruleNr < 256:
            print "binRule only supports ruleNr between 0 and 255!"
            sys.exit(1)

        self.ruleNr = ruleNr
        self.sizeX = sizeX
        self.sizeY = sizeY
        self.size = ( sizeX, sizeY )

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
        elif initConf == INIT_FILE and filename != "":
            self.importConf( filename )
        else:
            print "The initflag you've provided isn't available for the binRule-CA"
            print "Available initflags:"
            print "INIT_ZERO, INIT_ONES, INIT_RAND, INIT_FILE + filename"
            sys.exit(1)

        # init the rule
        self.ruleIdx = np.zeros( 8, int )
        for i in range( 8 ):
            if ( self.ruleNr & ( 1 << i ) ):
                self.ruleIdx[i] = 1

    def eventFunc( self, event ):
        pass

    def getDim( self ):
        return 1
    
    def getTitle( self ):
        return "Rule" + str( self.ruleNr )
    
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
        elif initConf == self.INIT_FILE and filename != "":
            self.importConf( filename )
        else:
            print "The initflag you've provided isn't available for the sandPile-CA"
            print "Available initflags:"
            print "INIT_ZERO, INIT_RAND, INIT_FILE + filename"
            sys.exit(1)
            
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
        
        
    def getDim ( self ):
        return 2

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

        
    def getTitle( self ):
        return "SandPile"

    def loopFunc( self ):
        self.addGrainRandomly()
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
        for filename in ( "images/balls/ball_black.png", "images/balls/ball_red.png"   , 
                          "images/balls/ball_blue.png" , "images/balls/ball_orange.png",
                          "images/balls/ball_green.png", "images/balls/ball_pink.png"  , 
                          "images/balls/ball_grey.png" , "images/balls/ball_white.png"  ):
            img = pygame.image.load( filename ).convert()
            self.palette.append( img )

    def getTitle( self ):
        return "BallPile"


########## von Neumann ##########
class vonNeumann ( CA ):
    palette = []
    
    def __init__( self, sizeX, sizeY, filename="" ):
        self.size = self.sizeX, self.sizeY = sizeX, sizeY

        self.currConf = np.zeros( (sizeX, sizeY), int )
        self.nextConf = np.zeros( (sizeX, sizeY), int )
        if filename != "":
            self.importConf( filename )

        for imgFile in ( "C00.jpg", "C01.jpg", "C10.jpg", "C11.jpg", 
                         "S000.jpg", "S00.jpg", "S01.jpg", "S0.jpg", 
                         "S10.jpg", "S11.jpg", "S1.jpg", "S.jpg", 
                         "T000.jpg", "T001.jpg", "T010.jpg", "T011.jpg", 
                         "T020.jpg", "T021.jpg", "T030.jpg", "T031.jpg", 
                         "T100.jpg", "T101.jpg", "T110.jpg", "T111.jpg", 
                         "T120.jpg", "T121.jpg", "T130.jpg", "T131.jpg", 
                         "U.jpg" ):
            img = pygame.image.load( filename ).convert()
            self.palette.append( img )

   
    def getDim( self ):
        return 2

    def getTitle( self ):
        return "vonNeumann"

    def loopFunc( self ):
        self.step()

    def step( self ):
        self.updateAllCellsWeaveInline()

#  
# All states are encoded in a bitmask:
#
#    <--MSB     20                  10                           LSB
#  ...... 0 0 0 0 0 0 0 0 0 0 0 0 0 X X u a1 a0 eps s2 s1 s0  e1 e0
#                                   | | | |  |  |    |  |  |  |  |-> current e
#  XX = 00 -> U            <--------| | | |  |  |    |  |  |  |----> next e
#  XX = 01 -> C            <----------| | |  |  |    |  |  |     
#  XX = 10 -> S                         | |  |  |    |  |  |-------> lsb on S
#  XX = 11 -> T                         | |  |  |    |  |----------> ...
#                                       | |  |  |    |-------------> msb on S
#  S{} is encoded as SMASK_111          | |  |  |
#                                       | |  |  |------------------> excited
#                                       | |  |---------------------> direction
#                                       | |------------------------> direction
#                                       |--------------------------> special
#

    def updateAllCellsWeaveInline( self ):
        vonNeumannCode = """
""";
}




#include <stdlib.h>

#line 1 "CA.py"
#define U              0
#define CMASK        512  // 1 << 9
#define SMASK       1024  // 2 << 9
#define TMASK       1536  // 3 << 9
#define CSTATEMASK     3  // 1 + 2
#define SSTATEMASK    28  // 4 + 8 + 16
#define TSTATEMASK   480  // 32 + 64 + 128 + 256
#define e0     1
#define e1     2
#define s0     4
#define s1     8
#define s2    16
#define s     28
#define eps   32
#define a0    64
#define a1   128
#define a    192
#define u    256

#define U(x) (x == 0)
#define C(x) (x & CMASK)
#define S(x) (x & SMASK)
#define T(x) (x & TMASK)

int code() {
  int i, j, k, l;
  int neighState[4];
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
	  if ( T(nbs[k]) && ( abs(k-((nbs[k]&a)>>6)) == 2) 
	       && (nbs[k]&u != state&u) && (nbs[k]&eps)  ) {
	    // (T.1)(alpha)
	    nconf( i, j ) = U;
	    break;
	  }
	}
	if ( k == 4 ) {
	  // (T.1)(beta)
	  for ( k = 0; k < 4; k++ ) {
	    if ( T(nbs[k]) && (abs(((nbs[k]&a)>>6)-((state&a)>>6)) != 2) 
		 && (nbs[k]&u == state&u ) && (nbs[k]&eps) ) {
	      // (T.1)(beta)(a)
	      nconf( i, j ) = state | eps;
	      break;
	    }
	    if ( C(nbs[k]) && (nbs[k]&e0) && (abs(k-((state&a)>>6)) != 2) ) {
	      // (T.1)(beta)(b)
	      nconf( i, j ) = state | eps;
	      break;
	    }
	  }
	}
	if ( k == 4 ) {
	  // (T.1)(gamme)
	  nconf( i, j ) = TMASK | u | a;
	}
      } 

      else if ( C(state) ) { // confluent state
	
      } 

      else if ( U(state) ) {  // unexcitable state
	// transition rule (T.3)
	for ( k = 0; k < 4; k++ ) {
	  if ( T(nbs[k]) && (abs(k-(nbs[k]&a)>>6) == 2) && (nbs[k]&eps) ) {
	    // (T.3)(alpha)
	    nconf( i, j ) = SMASK | s0 | s1 | s2;
	    break;
	  }
        }
	// (T.3)(beta)
	// doesn' change the state
      } 
      
      else if ( S(state) ) { // sensitized state
	// transition rule (T.4)
	l = state&(s1|s0);
	for ( k = 0; k < 4; k++ ) {
	  if ( T(nbs[k]) && (abs(k-(nbs[k]&a)>>6) == 2) && (nbs[k]&eps) ) {
	    // (T.4)(alpha)
	    nconf( i, j ) = SMASK | l<<1 + s0;
	    break;	    
	  }
	}
	if ( k == 4 ) {
	  // (T.4)(beta)
	  nconf( i, j ) = SMASK | l<<1;
	}
      } 

      else  {
	// error!
      }

    }
  }

     



      




        cconf = self.currConf
        nconf = self.nextConf
        sizeX = self.sizeX
        sizeY = self.sizeY
# try to reduce varpreparation by using a datastructure with size, all statemasks
# etc. and access it in the weavecode as array. 
        weave.inline( vonNeumannCode, [ 'cconf', 'nconf', 'sizeX', 'rule'],
                      type_converters = converters.blitz,
                      compiler = 'gcc' )
        self.currConf = self.nextConf.copy()

        
        C00 = 0
        C00 = 1
        C01 = 2
        C10 = 3
        C11 = 4
        S000 = 5
        S00 = 6
        S01 = 7
        S0 = 8
        S10 = 9
        S11 = 10
        S1 = 11
        S = 12
        T000 = 13
        T001 = 14 
        T010 = 15
        T011 = 16
        T020 = 17
        T021 = 18
        T030 = 19
        T031 = 20
        T100 = 21
        T101 = 22
        T110 = 23
        T111 = 24
        T120 = 25
        T121 = 26
        T130 = 27
        T131 = 28
        U = 29



if __name__ == "__main__":
    sizeX, sizeY = 10, 10
    pygame.init()
    screen = pygame.display.set_mode( (sizeX,sizeY), 0, 8 )
    surf = pygame.surface.Surface( (sizeX, sizeY ), 0, 8 )
    ca = ballPile( 10, 10 )
