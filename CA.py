import numpy as np
import pygame
import random
import sys
import os
from multiprocessing import Process, Pipe
import Histogram 

class CA():

    INIT_ZERO = 0
    INIT_ONES = 1
    INIT_RAND = 2
    
    palette = []

    def get_dim( self ):
        return 0

    def __init__( self ):
        print "function __init__() not implemented yet"

    def step( self ):
        self.updateAllCells()

    def conf( self ):
        return self.currConf

    def title( self ):
        return ""
    
    def quit( self ):
        print "function quit() not implemented yet"
    
    def loopFunc( self ):
        print "function loopFunc() not implemented yet"

    def eventFunc( self, event ):
        print "function eventFunc() not implemented yet"


class binRule( CA ):

    palette = [ (0,0,0), (255,255,255) ]

    def get_dim( self ):
        return 1
    
    def __init__ ( self, ruleNr, cells, lines, initConf ):
        self.ruleNr = ruleNr
        self.cells = cells
        self.lines = lines
        
        if initConf == self.INIT_ZERO:
            self.currConf = np.zeros( cells, int )
        elif initConf == self.INIT_ONES:
            self.currConf = np.ones( cells, int )
        elif initConf == self.INIT_RAND:
            self.currConf = np.zeros( cells, int )
            for i in range( cells ):
                self.currConf[i] = random.randint( 0, 1 )
        else:
            print "The initflag you've provided isn't available for the binRule-CA"
            print "Available initflags:"
            print "INIT_ZERO, INIT_ONES, INIT_RAND"
            sys.exit(1)
        self.nextConf = self.currConf.copy()
        
        # init the rule
        self.ruleIdx = np.zeros( 8, int )
        for i in range( 8 ):
            if ( self.ruleNr & ( 1 << i ) ):
                self.ruleIdx[i] = 1

    def updateAllCells( self ):
        for i in range( 1, self.cells-1 ):
            state = self.currConf[i-1] << 2
            state += self.currConf[i] << 1
            state += self.currConf[i+1]
            self.nextConf[i] = self.ruleIdx[state]

        self.currConf, self.nextConf = self.nextConf, self.currConf

    def step( self ):
        self.updateAllCells()

    def conf( self ):
        return self.currConf

    def title( self ):
        return "Rule" + str( self.ruleNr )
    
    def quit( self ):
        pass
    
    def loopFunc( self ):
        pass

    def eventFunc( self, event ):
        pass



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
    
    palette = [blue, white, yellow, darkred, grey, pink, green, red]
    
#    palette = [ black, white, grey, green, blue, pink, darkred, red ]

    # available histograms, concatenated by '|'
    HistVBars = 1
    HistTickerlines = 2

    info = ( "state 0", "state 1", "state 2", "state 3", "state 4", "state 5", "state 6", "state 7")
    
    def get_dim ( self ):
        return 2

    def __init__( self, sizeX, sizeY, initConf, masterQueue, histograms ):

        self.sizeX = sizeX
        self.sizeY = sizeY

        self.histogram = np.zeros( 8, int )
        
        if initConf == self.INIT_ZERO:
            self.currConf = np.zeros( ( sizeX, sizeY ), int )
            self.nextConf = np.zeros( ( sizeX, sizeY ), int )
            self.histogram[ 0 ] = self.sizeX * self.sizeY
        elif initConf == self.INIT_RAND:
            self.currConf = np.zeros( ( sizeX, sizeY ), int )
            for x in range( self.sizeX ):
                for y in range( self.sizeY ):
                    c = random.randint( 0, 3 )
                    self.currConf[ x, y ] = c
                    self.histogram[ c ] += 1
            self.nextConf = self.currConf.copy()
        else:
            print "The initflag you've provided isn't available for the sandpile-CA"
            print "Available initflags:"
            print "INIT_ZERO, INIT_RAND"
            sys.exit(1)
            
        self.masterQueue = masterQueue

        self.HistWindows = []
        if histograms & self.HistVBars:
            self.vertHisto = Histogram.VBars( 8, self.sizeX*self.sizeY, 
                                              self.palette, self.info )
            self.HistWindows.append( self.vertHisto ) 
        if histograms & self.HistTickerlines:
            self.TickerlinesHisto = Histogram.HTickerlines( 8, self.sizeX*self.sizeY, 
                                                            self.palette, self.info )
            self.HistWindows.append( self.TickerlinesHisto )
        
    def closeHistograms( self ):
        for h in self.HistWindows:
            h.close()

    def makeHistogram( self ):
        for i in range( 8 ):
            self.histogram[i] = 0
        for x in range( 1, self.sizeX-1 ):
            for y in range( 1, self.sizeY-1 ):
                self.histogram[ self.currConf[x,y] ] += 1

    def updateAllCells( self ):
        for x in range( 1, self.sizeX-1 ):
            for y in range( 1, self.sizeY-1 ):
                if self.currConf[ x, y ] > 3:
                    self.nextConf[ x, y ] = self.currConf[ x, y ] - 4
                    self.nextConf[ x+1, y ] = self.currConf[ x+1, y ] + 1
                    self.nextConf[ x-1, y ] = self.currConf[ x-1, y ] + 1
                    self.nextConf[ x, y+1 ] = self.currConf[ x, y+1 ] + 1
                    self.nextConf[ x, y-1 ] = self.currConf[ x, y-1 ] + 1

        self.currConf = self.nextConf.copy()
        self.makeHistogram()
        self.sendHistogram()

    def sendHistogram( self ):
        for h in self.HistWindows:
            h.update( self.histogram )

    def step( self ):
        self.updateAllCells()


    def conf( self ):
        return self.currConf

    def addGrain( self, x, y ):
        if self.currConf[ x, y ] <= 7:
            self.currConf[ x, y ] += 1
        else:
            print "You're trying to add a grain out of bounds!"

    def setState( self, x, y, s ):
        if 0 < s < 8 & 0 < x < (self.sizeX-1) & 0 < y < (self.sizeY-1):
            self.currConf[ x, y ] = s
    
    def addGrainRandomly( self ):
        x = random.randint( 1, self.sizeX-1 )
        y = random.randint( 1, self.sizeY-1 )
        self.addGrain( x, y )
        
    def title( self ):
        return "Sandpile"

    def quit( self ):
        self.closeHistograms()

    def loopFunc( self ):
        self.addGrainRandomly()
        
    def eventFunc( self, event ):
        x,y = event.pos
        if event.button == 1:
            pass
#            self.addGrain( x / scale, y / scale )
        if event.button == 3:
            pass
#            self.addGrain( x / scale, y / scale )
    


if __name__ == "__main__":
    cells,lines = 1000, 800
    ca = binRule( 110, cells, lines, 0 )
    print ca.title()
    pygame.init()
    screen = pygame.display.set_mode( (cells,lines), 0, 8 )
    surf = pygame.surface.Surface( (cells, lines ), 0, 8 )
    screen.set_palette( ((0,0,0),(255,255,255)) )
    surf.set_palette( ((0,0,0),(255,255,255)) )
    while 1:
        
        screen.blit( surf, (0,0) )
        pygame.display.update()
        ca.step()
