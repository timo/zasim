#!/usr/bin/python

import pygame
import numpy as np
import sys
from CA import sandpile


#size = sizeX, sizeY = argv[2], argv[2]
size = sizeX, sizeY = 20, 20
scale = 10.0
screenSize = int( sizeX * scale ), int( sizeY * scale )
screenXMin = 0
screenYMin = 0

ca = sandpile( sizeX, sizeY, sandpile.INIT_RAND )


pygame.init()
pygame.display.set_caption( "CASimulator - " + ca.title() )

simScreen = pygame.display.set_mode( screenSize, 0, 8 )
simSurface = pygame.surface.Surface( size, 0, 8 )
simScreen.set_palette( ca.palette )
simSurface.set_palette( ca.palette )


def zoom( f ):
    pass

def draw( data ):
    x = simScreen.get_width()
    y = simScreen.get_height()
    pygame.surfarray.blit_array( simSurface, data[screenXMin:x+screenXMin, screenYMin:y+screenYMin] )
    temp = pygame.transform.scale( simSurface, simScreen.get_size() )
    simScreen.blit( temp, (0,0) )

def resize( f ):
    global scale
    scale *= f
    screenSize = int( sizeX * scale ), int( sizeY * scale )
    pygame.display.set_mode( screenSize, 0, 8 )

def sim():
    while ( 1 ):
        for e in pygame.event.get():
            if e.type == pygame.MOUSEBUTTONDOWN:
                x,y = e.pos
                if e.button == 1:
                    ca.addGrain( x / scale, y / scale )
                if e.button == 3:
                    ca.addGrain( x / scale, y / scale )
                        
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_q:
                    sys.exit(1)
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

        ca.addGrainRandomly()
        ca.step()
        draw( ca.conf() )
        pygame.display.update()

 
if __name__ == "__main__":
    sim()
