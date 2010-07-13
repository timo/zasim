import numpy as np
import pygame
import random
import sys
import os
from multiprocessing import Process, Pipe
import Histogram 

class sandpile():
    INIT_ZERO = 0
    INIT_RAND = 1
    
    # currConf is the current state
    # nextConf is the next step after the current
    
    white = 255,255,255
    black = 0,0,0
    red = 255,0,0
    green = 0,255,0
    blue = 0,0,255
    grey = 170,170,170
    pink = 250,40,230
    darkred = 95,0,16

    palette = [ black, white, grey, green, blue, pink, darkred, red ]

#        pygame.display.set_caption("CASimulator - Sandpile - Info" )

    # available histograms, concatenated by '|'
    HistVBars = 1
    HistTickerlines = 2

    def __init__( self, sizeX, sizeY, initConf, masterQueue, histograms ):

        self.sizeX = sizeX
        self.sizeY = sizeY

        self.histogram = np.zeros( 8, int )
        
        if initConf == self.INIT_ZERO:
            self.currConf = np.zeros( ( sizeX, sizeY ), int )
            self.nextConf = np.zeros( ( sizeX, sizeY ), int )
            self.histogram[ 0 ] = self.sizeX * self.sizeY

        if initConf == self.INIT_RAND:
            self.currConf = np.zeros( ( sizeX, sizeY ), int )
            for x in range( self.sizeX ):
                for y in range( self.sizeY ):
                    c = random.randint( 0, 3 )
                    self.currConf[ x, y ] = c
                    self.histogram[ c ] += 1
            self.nextConf = self.currConf.copy()
            
        self.masterQueue = masterQueue

        self.HistWindows = []
        if histograms & self.HistVBars:
            self.vertHisto = Histogram.VBars( 8, self.sizeX*self.sizeY, self.palette )
            self.HistWindows.append( self.vertHisto ) 
        if histograms & self.HistTickerlines:
            self.TickerlinesHisto = Histogram.HTickerlines( 8, self.sizeX*self.sizeY, self.palette )
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


    
