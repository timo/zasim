#!/usr/bin/python

import pygame
import numpy as np
import sys
import time
from multiprocessing import Queue
from CA import sandpile, binRule


#size = sizeX, sizeY = argv[2], argv[2]
size = sizeX, sizeY = 2000,2000
scale = 0.5
screenSize = int( sizeX * scale ), int( sizeY * scale )

simQueue = Queue()

ca = sandpile( sizeX, sizeY, sandpile.INIT_RAND, simQueue,  sandpile.HistTickerlines )
#ca = binRule( 110, sizeX, sizeY, binRule.INIT_ONES )
pygame.init()
pygame.display.set_caption( "CASimulator - " + ca.title() )
clock = pygame.time.Clock()

simScreen = pygame.display.set_mode( screenSize, 0, 8 )
simScreen.set_palette( ca.palette )

class Blitter():
    def __init__( self, size, palette ):
        self.screenXMin = 0
        self.screenYMin = 0
        self.zoomIdx = 0
        self.zoomSizes = []
        self.zoomSizes.append( size )
        self.zoomSizes.append( (size[0]*3/4, size[1]*3/4 ) )
        i = 2
        while self.zoomSizes[len(self.zoomSizes)-1][0] != (size[0]/i) and self.zoomSizes[len(self.zoomSizes)-1][1] != (size[1]/i):
            self.zoomSizes.append( (size[0]/i,size[1]/i) )
            i += 1
        self.surface = pygame.surface.Surface( size, 0, 8 )
        self.surface.set_palette( palette )
        self.subSurf = self.surface.subsurface( (0,0), size )

    def getSurface( self ):
        return self.surface

    def getSubSurface( self ):
        return self.subSurf

    def scroll( self, key ):
        if key == pygame.K_UP and self.screenYMin > 0:
            self.screenYMin -= 1
        if key == pygame.K_DOWN and ( self.screenYMin + self.subSurf.get_height() + 1 < sizeY - 1 ):
            self.screenYMin += 1
        if key == pygame.K_LEFT and self.screenXMin > 0:
            self.screenXMin -= 1
        if key == pygame.K_RIGHT and ( self.screenXMin + self.subSurf.get_width() + 1 < sizeX - 1 ):
            self.screenXMin += 1
    
    def zoom( self, c ):
        if c == "0":
            self.zoomIdx = 0
        elif c == "1" and self.zoomIdx < len(self.zoomSizes)-1:
            self.zoomIdx += 1
        elif c == "2" and self.zoomIdx > 0:
            self.zoomIdx -= 1
        self.subSurf = self.surface.subsurface( (0,0), self.zoomSizes[self.zoomIdx] )

class Blitter1D(Blitter):
    def __init__( self, size, palette ):
        Blitter.__init__( self, size, palette )
        self.newlineSurface = self.surface.subsurface((0,size[1]-1,size[0],1))
        self.array = np.zeros( (1,size[0]), int )

    def blitArray( self, data ):
        self.surface.scroll( 0, -1 )
        self.array[0] = ( data )
        pygame.surfarray.blit_array( self.newlineSurface, np.transpose(self.array) )

class Blitter2D(Blitter):
    def __init__( self, size, palette ):
        Blitter.__init__( self, size, palette )

    def blitArray( self, data ):
        if self.screenXMin + self.subSurf.get_width() > sizeX or self.screenYMin + self.subSurf.get_height() > sizeY:
            self.screenXMin = sizeX-self.subSurf.get_width()
            self.screenYMin = sizeY-self.subSurf.get_height()
        pygame.surfarray.blit_array( 
            self.subSurf, 
            data[self.screenXMin:self.screenXMin+self.subSurf.get_width(),
                 self.screenYMin:self.screenYMin+self.subSurf.get_height()]
            )
        

        

if ca.get_dim() == 1:
    blitter = Blitter1D( size, ca.palette )
elif ca.get_dim() == 2:
    blitter = Blitter2D( size, ca.palette )
                          

def draw( data ):
    blitter.blitArray( data )
    temp = pygame.transform.scale( blitter.getSubSurface(), simScreen.get_size() )
    simScreen.blit( temp, (0,0) )

def resize( f ):
    global scale
    scale *= f
    screenSize = int( sizeX * scale ), int( sizeY * scale )
    pygame.display.set_mode( screenSize, 0, 8 )

def sim():
    looping = False
    while ( 1 ):
        clock.tick()
        pygame.display.set_caption( "CASimulator - " + ca.title() + " - " 
                                    + str(int(clock.get_fps())) + "fps" )
        for e in pygame.event.get():
            if e.type == pygame.MOUSEBUTTONDOWN:
                ca.eventFunc( e )
                        
            if e.type == pygame.KEYDOWN:
                if e.unicode == "q":
                    pygame.quit()
                    ca.quit()
                    sys.exit(1)

                # display-related functions
                if e.unicode == "+":
                    resize(1.1)
                if e.unicode == "-":
                    resize(0.9)
                if e.unicode == "0" or e.unicode == "1" or e.unicode == "2":
                    blitter.zoom( e.unicode )
                if e.key == pygame.K_RIGHT or e.key == pygame.K_LEFT or e.key == pygame.K_UP or e.key == pygame.K_DOWN :
                    blitter.scroll( e.key )

#        if looping == True:
        ca.loopFunc()
        ca.step()
        draw( ca.conf() )
        pygame.display.update()

 
if __name__ == "__main__":
    sim()
