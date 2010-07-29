#!/usr/bin/python

import pygame
import numpy as np
import sys
import time
from multiprocessing import Queue
from CA import sandpile, binRule


#size = sizeX, sizeY = argv[2], argv[2]
size = sizeX, sizeY = 300,300
scale = 1.0
screenSize = int( sizeX * scale ), int( sizeY * scale )
screenXMin = 0
screenYMin = 0

simQueue = Queue()

#ca = sandpile( sizeX, sizeY, sandpile.INIT_RAND, simQueue, sandpile.HistVBars | sandpile.HistTickerlines )
ca = binRule( 110, sizeX, sizeY, binRule.INIT_ONES )
pygame.init()

class Blitter1D():
    def __init__( self, size, palette ):
        self.surface = pygame.surface.Surface( size, 0, 8 )
        self.surface.set_palette( palette )
        self.newlineSurface = self.surface.subsurface((0,size[1]-1,size[0],1))
        self.array = np.zeros( (1,size[0]), int )
#        self.array = np.zeros( (size[0],1), int )

    def blitArray( self, data ):
        self.surface.scroll( 0, -1 )

#verbessern!!!!!!!
        self.array[0] = ( data )
        pygame.surfarray.blit_array( self.newlineSurface, np.transpose(self.array) )

#        for i in range( len(data) ):
#            self.array[i,0] = data[i]
#        pygame.surfarray.blit_array( self.newlineSurface, self.array )

    def surface( self ):
        return self.surface


class Blitter2D():
    def __init__( self, size, palette ):
        self.surface = pygame.surface.Surface( size, 0, 8 )
        self.surface.set_palette( palette )
        
    def blitArray( self, data ):
        pygame.surfarray.blit_array( 
            self.surface, 
            data#[screenXMin:x+screenXMin, screenYMin:y+screenYMin]
            )
        
    def surface( self ):
        return self.surface

        

if ca.get_dim() == 1:
    blitter = Blitter1D( size, ca.palette )
elif ca.get_dim() == 2:
    blitter = Blitter2D( size, ca.palette )
                          

pygame.display.set_caption( "CASimulator - " + ca.title() )

simScreen = pygame.display.set_mode( screenSize, 0, 8 )
simScreen.set_palette( ca.palette )

clock = pygame.time.Clock()

def zoom( f ):
    print "zoom, ", f
    pass

def draw( data ):
    x = simScreen.get_width()
    y = simScreen.get_height()
    blitter.blitArray( data )
#    pygame.surfarray.blit_array( simSurface, data[screenXMin:x+screenXMin, screenYMin:y+screenYMin] )
    temp = pygame.transform.scale( blitter.surface, simScreen.get_size() )
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
                if e.key == pygame.K_q:
                    pygame.quit()
                    ca.quit()
                    sys.exit(1)

                # display-related functions
                if e.key == pygame.K_PLUS:
                    resize(1.1)
                if e.key == pygame.K_MINUS:
                    resize(0.9)
                if e.key == pygame.K_0:
                    zoom(0)
                if e.key == pygame.K_1:
                    zoom(1)
                if e.key == pygame.K_2:
                    zoom(2)
                if e.key == pygame.K_RIGHT:
                    screenXMin += 1
                if e.key == pygame.K_LEFT:
                    screenXMin -= 1
                if e.key == pygame.K_UP:
                    screenYMin -= 1
                if e.key == pygame.K_DOWN:
                    screenYMin += 1

        if looping == True:
            ca.loopFunc()
            ca.step()
            draw( ca.conf() )
        pygame.display.update()

 
if __name__ == "__main__":
    sim()
