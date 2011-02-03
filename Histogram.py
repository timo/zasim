#!/usr/bin/python

import pygame
from multiprocessing import Process, Pipe, Queue
import random
import sys
import time
import numpy as np 


black = 0,0,0
white = 255,255,255
red = 255,0,0
green = 0,255,0
blue = 0,0,255
grey = 170,170,170
pink = 250,40,230
darkred = 95,0,16
yellow = 255,240,0

palette1 = [white]
palette2 = [blue, red]
palette3 = [blue, green, red]
palette4 = [blue, pink, green, red]
palette5 = [blue, grey, pink, green, red]
palette6 = [blue, darkred, grey, pink, green, red]
palette7 = [blue, yellow, darkred, grey, pink, green, red]
palette8 = [blue, white, yellow, darkred, grey, pink, green, red]
palettes = ( palette1, palette2, palette3, palette4, 
             palette5, palette6, palette7, palette8 )


## abstract superclass, dont use this one ##
class Histogram():
    def __init__ ( self, N, maxVal, palette, info=() ):
        if N > 8:
            print "maximum N is 8 at the moment :("
            sys.exit(1)
        self.N = N
        if maxVal == 0:
            print "havent implemented arg2 = 0!"
            sys.exit(1)
        self.maxVal = maxVal
        if len(palette) == 0:
            if 1 <= N <= 8:
                self.activePalette = palettes[N-1]
            else:
                print "hey, provide a palette"
                sys.exit(1)
        else:
            for i in range(len(palette)):
                if palette[i] == (0,0,0):
                    print "Warning: You have provided BLACK as your color no.", i
                    print "You wont see the black bar on a black background... "
            self.activePalette = palette
        
        self.eventQueue = Queue()
        self.QUIT = 0
        self.SHOW = 1
        self.HIDE = 2
        
        self.info = info
        if len( info ) != self.N:
            print "You didn't provide the correct number of info-elements"
            print len(info), self.N
            sys.exit(1)

        self.conn1, self.conn2 = Pipe()
        self.p = Process( target=self.runProcess, args=( self.conn1, ))
        self.p.start()
        
    def show ( self ):
        self.eventQueue.put( self.SHOW )

    def hide ( self ):
        self.eventQueue.put( self.HIDE )

    def close ( self ):
        self.eventQueue.put( self.QUIT )
        
    def handleNonPygameEvents( self ):
        while not(self.eventQueue.empty()):
            e = self.eventQueue.get()
            if e == self.QUIT:
                pygame.quit()
                return -1
            if ( e == self.SHOW ) & ( not( pygame.display.get_init() ) ):
                pygame.display.set_mode ( self.histWindowSize, 0 )
                return 0
            if ( e == self.HIDE ) & ( pygame.display.get_init() ):
                pygame.display.quit()
                
        
    def set_title ( self, title ):
        pygame.display.set_caption( str(title) )

    def update( self, hist ):
        if len(hist) != self.N:
            print "Not the correct number of elements for the histogram!"
            return
        else:
            self.conn2.send( hist )

    def getInfoPositions( self, spaceX ):
        fontsize = 20
        myfont = pygame.font.SysFont( "None", fontsize )
        infoPositions = []
        self.infoColorRectSize = 15
        pos = X, Y = 20,10
        for i in self.info:
            if (X + self.infoColorRectSize 
                + 10 + myfont.size(str(i))[0]) > self.histWindowSize[0]:
                Y += 20
                X = 20
            pos = X, Y
            infoPositions.append( (str(i), pos) )
            X += self.infoColorRectSize + 10 + myfont.size(str(i))[0] + 20
        Y += 30
        pos = X,Y
        infoPositions.append( ("eof", pos) )
        return infoPositions

#
# if you add another subclass of Histogram, try to use these conventions
# for variablenames and sizes
#
# total surface: surf
# -------------------------------------------------------------
# | scaleSubSurf  | histSubSurf                               |
# |               |                                           |
# |               |                  ^                        |
# |               |                  |                        |
# | <- offsetX -> |        <- histWindowSize ->               |
# |               |                  |                        |
# |               |                  v                        |
# |               |                                           |
# -------------------------------------------------------------
# | infoSubSurf                    ^                          |
# |                                |                          |
# |                             offsetY                       |
# |                                |                          |
# |                                v                          |
# -------------------------------------------------------------
#

## use these! ##
class VBars(Histogram):
    def runProcess( self, conn ):
        pygame.display.init()
#        pygame.display.set_caption( "VBar-Histogram" )
        print "iuzgozg"
        # 20 pixels per bar, 30 pixels between bars, 65 pixels on each side
        self.histWindowSize = ( ((self.N*20)+((self.N-1)*30)+65+65), 100 )
        self.offsetX = 55
        infoPos = self.getInfoPositions( self.histWindowSize[0]+self.offsetX )
        self.offsetY = infoPos[len(infoPos)-1][1][1]
        print "iuzgozg"

        # setting surface up and dividing it into subsurfs
        self.surf = pygame.display.set_mode( (self.histWindowSize[0] + self.offsetX,
                                              self.histWindowSize[1] + self.offsetY) )
        print "iuzgozg"
        self.scaleSubSurf = self.surf.subsurface( (0, 0, 
                                                   self.offsetX, 
                                                   self.histWindowSize[1] ) )
        self.histSubSurf = self.surf.subsurface( ( ( self.offsetX, 0 ), 
                                                   self.histWindowSize )  )
        self.infoSubSurf = self.surf.subsurface( (0, self.histWindowSize[1],
                                                  self.histWindowSize[0] + self.offsetX,
                                                  self.offsetY ) )
        print "iuzgozg"
        
        # scale         
        pygame.draw.line( self.scaleSubSurf, white, (50,self.histWindowSize[1]*0.1), 
                          (50,self.histWindowSize[1]*0.9), 2 )
        pygame.draw.line( self.scaleSubSurf, white, (45,self.histWindowSize[1]*0.1), 
                          (55,self.histWindowSize[1]*0.1), 2 )
        pygame.draw.line( self.scaleSubSurf, white, (45,self.histWindowSize[1]/2), 
                          (55,self.histWindowSize[1]/2), 2 )
        pygame.draw.line( self.scaleSubSurf, white, (45,self.histWindowSize[1]*0.9), 
                          (55,self.histWindowSize[1]*0.9), 2 )
        fontsize = 20
        myfont = pygame.font.SysFont( "None", fontsize )
        self.scaleSubSurf.blit(myfont.render( str(self.maxVal), 0, white), 
                               (15, self.histWindowSize[1]*0.087) )
        self.scaleSubSurf.blit(myfont.render( str(self.maxVal/2), 0, white), 
                               (15, self.histWindowSize[1]/2-5) )
        self.scaleSubSurf.blit(myfont.render("0", 0, white), 
                               (15, self.histWindowSize[1]-20) )
        
        # horizontal dividing line
        pygame.draw.line( self.surf, white, ( 0, self.histWindowSize[1] ), 
                          ( self.histWindowSize[0]+self.offsetX, 
                            self.histWindowSize[1]), 
                          2 )
        
        # info
        for i in range( self.N ):
            pygame.draw.rect( self.infoSubSurf, self.activePalette[i], 
                              ( infoPos[i][1][0], infoPos[i][1][1] , 
                                self.infoColorRectSize, self.infoColorRectSize), 
                              0 )
            self.infoSubSurf.blit( myfont.render( infoPos[i][0], 0, white ), 
                                   ( infoPos[i][1][0] + self.infoColorRectSize + 10, 
                                     infoPos[i][1][1]) )
        # main loop
        while 1:
            if self.handleNonPygameEvents() == -1:
                return
            for e in pygame.event.get():
               if e.type == pygame.KEYDOWN:
                   if e.key == pygame.K_m:
                       self.hide()
            
            hist = conn.recv()
            for i in range(len(hist)):
                rectHeight = -1 * self.histWindowSize[1]*0.8 * hist[i] / self.maxVal
                blackrect = ( 65+i*50, self.histWindowSize[1]*0.05, 
                              20, self.histWindowSize[1]*0.9 )
                rect = (65+i*50, self.histWindowSize[1]*0.9, 
                        20, rectHeight )
                pygame.draw.rect(self.histSubSurf, black, blackrect, 0 )
                pygame.draw.rect(self.histSubSurf, self.activePalette[i], rect, 0 )
            pygame.display.update()

        

class HContinuouslines( Histogram ):
    def runProcess( self, conn ):
        pygame.init()
        pygame.display.set_caption( "HContinuouslines-Histogram" )

        self.histWindowSize = ( 500, 200 )
        self.offsetX = 60
        infoPos = self.getInfoPositions( self.histWindowSize[0] + self.offsetX )
        self.offsetY = infoPos[len(infoPos)-1][1][1]

        # setting surface up and dividing it into subsurfs
        self.surf = pygame.display.set_mode( (self.histWindowSize[0] + self.offsetX, 
                                              self.histWindowSize[1] + self.offsetY ) ) 
        self.scaleSubSurf = self.surf.subsurface( ( 0, 0,
                                                    self.offsetX, 
                                                    self.histWindowSize[1] ) )
        self.histSubSurf = self.surf.subsurface( ( (self.offsetX, 0 ), 
                                                   self.histWindowSize ) )
        self.infoSubSurf = self.surf.subsurface( ( 0, self.histWindowSize[1], 
                                                   self.histWindowSize[0]+self.offsetX,
                                                   self.offsetY ) )
        
        # scale
        pygame.draw.line( self.scaleSubSurf, white, (50,self.histWindowSize[1]*0.05), 
                          (50,self.histWindowSize[1]*0.95), 2 )
        pygame.draw.line( self.scaleSubSurf, white, (45,self.histWindowSize[1]*0.05), 
                          (55,self.histWindowSize[1]*0.05), 2 )
        pygame.draw.line( self.scaleSubSurf, white, (45,self.histWindowSize[1]/2), 
                          (55,self.histWindowSize[1]/2), 2 )
        pygame.draw.line( self.scaleSubSurf, white, (45,self.histWindowSize[1]*0.95), 
                          (55,self.histWindowSize[1]*0.95), 2 )
        fontsize = 20
        myfont = pygame.font.SysFont( "None", fontsize )
        self.scaleSubSurf.blit(myfont.render( str(self.maxVal), 0, white), 
                               (15, self.histWindowSize[1]*0.075) )
        self.scaleSubSurf.blit(myfont.render( str(self.maxVal/2), 0, white), 
                               (15,self.histWindowSize[1]/2-5 ) )
        self.scaleSubSurf.blit(myfont.render( "0", 0, white), 
                               (15, self.histWindowSize[1]-25) )
        
        # horizontal dividing line
        pygame.draw.line( self.surf, white, ( 0, self.histWindowSize[1] ), 
                          (self.histWindowSize[0] + self.offsetX, 
                           self.histWindowSize[1]), 
                          2 )
        
        # info
        for i in range( self.N ):
            pygame.draw.rect( self.infoSubSurf, self.activePalette[i], 
                              ( infoPos[i][1][0], infoPos[i][1][1] , 
                                self.infoColorRectSize, self.infoColorRectSize), 
                              0 )
            self.infoSubSurf.blit( myfont.render( infoPos[i][0], 0, white ), 
                                   ( infoPos[i][1][0] + self.infoColorRectSize + 10, 
                                     infoPos[i][1][1]) )

        # history and de-/enabling individual lines
        showFlags = np.ones( 8, bool )
        history = np.zeros( (self.N, 2), int )
        scrollSpeed = 5
        posX = self.histWindowSize[0] - (3*scrollSpeed)
        for i in range(self.N):
            history[i] = (posX, self.histWindowSize[1]/2)


        #main loop
        while 1:
            self.handleNonPygameEvents()
            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_0:
                        showFlags[0] = not(showFlags[0])
                    if e.key == pygame.K_1:
                        showFlags[1] = not(showFlags[1])
                    if e.key == pygame.K_2:
                        showFlags[2] = not(showFlags[2])
                    if e.key == pygame.K_3:
                        showFlags[3] = not(showFlags[3])
                    if e.key == pygame.K_4:
                        showFlags[4] = not(showFlags[4])
                    if e.key == pygame.K_5:
                        showFlags[5] = not(showFlags[5])
                    if e.key == pygame.K_6:
                        showFlags[6] = not(showFlags[6])
                    if e.key == pygame.K_7:
                        showFlags[7] = not(showFlags[7])
                    if e.key == pygame.K_q:
                        self.close()
                    if e.key == pygame.K_h:
                        self.hide()
            
            hist = conn.recv()
            self.histSubSurf.scroll(-scrollSpeed,0)

            for i in range(len(hist)):
                posY = ( self.histWindowSize[1]*0.95 - 
                         (self.histWindowSize[1]* 0.9 * hist[i]) / self.maxVal )
                if showFlags[i] == True:
                    pygame.draw.line( self.histSubSurf, self.activePalette[i], 
                                      history[i], (posX,posY), 2 )
                history[i] = (posX,posY)
            pygame.display.update()




class HTickerlines( Histogram ):
    def runProcess( self, conn ):
        pygame.init()
        pygame.display.set_caption( "HTickerlines-Histogram" )

        self.histWindowSize = ( 500, 200 )
        self.offsetX = 60
        infoPos = self.getInfoPositions( self.histWindowSize[0] + self.offsetX )
        self.offsetY = infoPos[len(infoPos)-1][1][1]
        
        # setting surface up and dividing it into subsurfs
        self.surf = pygame.display.set_mode( (self.histWindowSize[0] + self.offsetX,
                                              self.histWindowSize[1] + self.offsetY) )
        self.scaleSubSurf = self.surf.subsurface( ( 0, 0,
                                                    self.offsetX,
                                                    self.histWindowSize[1] ) )
        self.histSubSurf = self.surf.subsurface( ( ( self.offsetX, 0 ),
                                                   self.histWindowSize ) )
        self.infoSubSurf = self.surf.subsurface( ( 0, self.histWindowSize[1],
                                                   self.histWindowSize[0]+self.offsetX,
                                                   self.offsetY ) )

        # scale
        pygame.draw.line( self.scaleSubSurf, white, (50,self.histWindowSize[1]*0.05), 
                          (50,self.histWindowSize[1]*0.95), 2 )
        pygame.draw.line( self.scaleSubSurf, white, (45,self.histWindowSize[1]*0.05), 
                          (55,self.histWindowSize[1]*0.05), 2 )
        pygame.draw.line( self.scaleSubSurf, white, (45,self.histWindowSize[1]/2), 
                          (55,self.histWindowSize[1]/2), 2 )
        pygame.draw.line( self.scaleSubSurf, white, (45,self.histWindowSize[1]*0.95), 
                          (55,self.histWindowSize[1]*0.95), 2 )
        fontsize = 20
        myfont = pygame.font.SysFont( "None", fontsize )
        self.surf.blit(myfont.render( str(self.maxVal), 0, white), 
                       (15, self.histWindowSize[1]*0.075) )
        self.surf.blit(myfont.render( str(self.maxVal/2), 0, white), 
                       (15,self.histWindowSize[1]/2-5 ) )
        self.surf.blit(myfont.render( "0", 0, white), 
                       (15, self.histWindowSize[1]-25) )

        # horizontal dividing line
        pygame.draw.line( self.surf, white, ( 0, self.histWindowSize[1] ), 
                          ( self.histWindowSize[0] + self.offsetX, 
                            self.histWindowSize[1]), 
                          2 )
        
        # info
        for i in range( self.N ):
            pygame.draw.rect( self.infoSubSurf, self.activePalette[i], 
                              ( infoPos[i][1][0], infoPos[i][1][1] , 
                                self.infoColorRectSize, self.infoColorRectSize), 
                              0 )
            self.infoSubSurf.blit( myfont.render( infoPos[i][0], 0, white ), 
                                   ( infoPos[i][1][0] + self.infoColorRectSize + 10, 
                                     infoPos[i][1][1] ) )
        
        # history and de-/enabling individual lines
        showFlags = np.ones( 8, bool )
        history = np.zeros( ( self.N, 2 ), int )
        for i in range(self.N):
            history[i] = ( self.offsetX, self.histWindowSize[1]/2)
        posX = 0

        # main loop
        while 1:
            self.handleNonPygameEvents()
            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_0:
                        showFlags[0] = not(showFlags[0])
                    if e.key == pygame.K_1:
                        showFlags[1] = not(showFlags[1])
                    if e.key == pygame.K_2:
                        showFlags[2] = not(showFlags[2])
                    if e.key == pygame.K_3:
                        showFlags[3] = not(showFlags[3])
                    if e.key == pygame.K_4:
                        showFlags[4] = not(showFlags[4])
                    if e.key == pygame.K_5:
                        showFlags[5] = not(showFlags[5])
                    if e.key == pygame.K_6:
                        showFlags[6] = not(showFlags[6])
                    if e.key == pygame.K_7:
                        showFlags[7] = not(showFlags[7])
                    if e.key == pygame.K_h:
                        self.hide()


            hist = conn.recv()
                    
            if posX % 100 == 0: # (*)
                self.histSubSurf.fill( black, ( ( posX % self.histWindowSize[0]),
                                                0.05*self.histWindowSize[1], 
                                                0.2 *self.histWindowSize[0],
                                                self.histWindowSize[1]*0.95 ), 0 )
                
            for i in range(len(hist)):
                posY = ( self.histWindowSize[1]*0.95 - 
                         (self.histWindowSize[1]*0.9) * hist[i] / self.maxVal )
                pos = ( posX % self.histWindowSize[0], posY)
                if pos[0] - history[i][0] < 0:
                    history[i][0] = 0
                if showFlags[i] == True:
                    pygame.draw.line( self.histSubSurf, self.activePalette[i], 
                                      history[i], pos, 2 )
                    
                history[i] = pos
            pygame.display.update()
            
            posX += 5 #if you change this, remember (*)



if __name__ == "__main__":
    maxi = 1254
    hists = []
    hists.append( HTickerlines( 4, maxi, (), 
                                ( "State 0", "State 1", "State 2", "State 3" ) ) )
    hists.append( VBars( 4, maxi, (), ("State 0", "State 1", "State 2", "State 3") ) )
    hists.append( HContinuouslines( 4, maxi, (), 
                                    ( "State 0", "State 1", "State 2", "State 3" ) ) )
    i = 0
    while i < 2000:
        i = i+1
        j = random.randint( 1, maxi )
        if j < maxi:
            k = random.randint( 1, maxi-j)
        else:
            k = 0
        if j + k < maxi:
            l = random.randint( 1, maxi-j-k)
        else:
            l = 0
        m = maxi - j - k - l
        t =(j,k,l,m)
        for h in hists:
            h.update( t )

    for h in hists:
        h.close()



    
