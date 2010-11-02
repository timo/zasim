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

# for catpile
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
#        try:
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
#        except:
#            print "there was a problem with exporting"

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
        
#        try:
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

#        except:
#            print "there was an error while importing from file", filename

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
#            self.currConf = np.zeros( sizeX, int )
#            self.nextConf = np.zeros( sizeY, int )
            self.currConf = np.zeros( (sizeX,1), int )
            self.nextConf = np.zeros( (sizeX,1), int )
        elif self.getDim() == 2:
            self.currConf = np.zeros( self.size, int )
            self.nextConf = np.zeros( self.size, int )
#        print sizeX, sizeY
        
    def setConf( self, conf ):
        if conf.size != self.currConf.size:
            if self.getDim() == 1:
                self.resize( conf[0].size )
            elif self.getDim() == 2:
                self.resize( conf[0].size, conf[1].size )
        self.currConf = conf.copy()
        self.nextConf = conf.copy()

    def step( self ):
        pass


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
#            self.currConf = np.zeros( (sizeX), int )
#            self.nextConf = np.zeros( (sizeX), int )
            self.currConf = np.zeros( (sizeX, 1), int )
            self.nextConf = np.zeros( (sizeX, 1), int )
        elif initConf == self.INIT_ONES:
#            self.currConf = np.ones( (sizeX), int )
#            self.nextConf = np.ones( (sizeX), int )
            self.currConf = np.ones( (sizeX, 1), int )
            self.nextConf = np.ones( (sizeX, 1), int )
        elif initConf == self.INIT_RAND:
#            self.currConf = np.ones( (sizeX), int )
            self.currConf = np.zeros( (sizeX, 1), int )
            self.nextConf = np.zeros( (sizeX, 1), int )
            for i in range( sizeX ):
#                self.currConf[i] = random.randint( 0, 1 )
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
        CA.step( self )
#        self.updateAllCellsPy()
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
  state = cconf(i-1) << 2;
  state += cconf(i) << 1;
  state += cconf(i+1);
  nconf(i) = rule(state);
}
nconf(1) = nconf(sizeX-3);
nconf(sizeX-2) = nconf(2);
"""
### just delete one of these!
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




########## sandpile #############
class sandpile( CA ):
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
            print "The initflag you've provided isn't available for the sandpile-CA"
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
        return "Sandpile"

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
#        self.addGrain( self.sizeX/2, self.sizeY/2 )
  #      self.updateAllCellsPyHistImpl()
#        self.updateAllCellsPyHistExpl()
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
        




########## catpile #############
class catpile( sandpile ):

    def __init__( self, sizeX, sizeY, initConf ):
        self.readImage( "cat.jpg" )
            
    def readImage( self, filename ):
        dummy_data = Image.open(filename)
        dummy_data = dummy_data.convert("I")

        image = fromimage(dummy_data)
        for i in range(len(image)):
            for j in range(len(image[0])):
                image[i,j] /= 32
#        print image[10,10]
#        print image
        self.currConf = image
        self.nextConf = image
        print image[0:10,0:10]
        i = np.transpose(image)
        print i[0:10,0:10]
#       return
        self.currConf = np.transpose(image)
        print self.currConf
        self.nextConf = self.currConf.copy()

    def getTitle( self ):
        return "Catpile"


class ballPile( CA ):
    palette=[]
    def __init__( self, sizeX, sizeY ):
        self.size = self.sizeX, self.sizeY = sizeX, sizeY
        
        pygame.init()
        pygame.display.set_mode( (sizeX,sizeY), 0, 8 )
        
        for filename in ( "images/ball_black.png", "images/ball_red.png"   , 
                          "images/ball_blue.png" , "images/ball_orange.png",
                          "images/ball_green.png", "images/ball_pink.png"  , 
                          "images/ball_grey.png" , "images/ball_white.png"  ):
            img = pygame.image.load( filename ).convert()
            self.palette.append( img )
            
        self.currConf = np.zeros( ( sizeX, sizeY ), int )
#        for x in range(self.sizeX):
#            for y in range( self.sizeY ):
#                self.currConf[x,y] = (x+y)%8
        self.nextConf = np.zeros( ( sizeX, sizeY ), int )
#        self.nextConf = self.currConf.copy()


    def addGrainRandomly( self ):
        x = random.randint( 1, self.sizeX-1 )
        y = random.randint( 1, self.sizeY-1 )
        while self.currConf[ x, y ] >= 7:
            x = random.randint( 1, self.sizeX-1 )
            y = random.randint( 1, self.sizeY-1 )
        self.currConf[ x, y ] += 1


    def getDim( self ):
        return 2

    def loopFunc( self ):
        self.addGrainRandomly()
        self.step()

    def step( self ):
        self.updateAllCellsWeaveInline()

    def updateAllCellsWeaveInline( self ):
        code = """
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
        weave.inline( code, ['cconf', 'nconf', 'sizeX', 'sizeY' ],
                      type_converters = converters.blitz,
                      compiler = 'gcc' )
        self.currConf = self.nextConf.copy()


if __name__ == "__main__":
    sizeX, sizeY = 10, 10
    pygame.init()
    screen = pygame.display.set_mode( (sizeX,sizeY), 0, 8 )
    surf = pygame.surface.Surface( (sizeX, sizeY ), 0, 8 )
    ca = ballPile( 10, 10 )

