import pygame
from multiprocessing import Process, Pipe
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

class Histogram():
    def __init__ ( self, N, maxVal, palette ):
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

        self.conn1, self.conn2 = Pipe()
        self.p = Process( target=self.runProcess, args=( self.conn1, ))
        self.p.start()
        
    def set_title ( self, title ):
        pygame.display.set_caption( str(title) )


class VBars(Histogram):
    def runProcess( self, conn ):
        pygame.init()
        self.histWindowSize = ( ((self.N*20)+((self.N-1)*30)+130)+50 , 100 )
        self.surf = pygame.display.set_mode( self.histWindowSize )
        pygame.display.set_caption( "VBar-Histogram" )
        pygame.draw.line( self.surf, white, (50,self.histWindowSize[1]*0.1), 
                          (50,self.histWindowSize[1]*0.9), 2 )
        pygame.draw.line( self.surf, white, (45,self.histWindowSize[1]*0.1), 
                          (55,self.histWindowSize[1]*0.1), 2 )
        pygame.draw.line( self.surf, white, (45,self.histWindowSize[1]/2), 
                          (55,self.histWindowSize[1]/2), 2 )
        pygame.draw.line( self.surf, white, (45,self.histWindowSize[1]*0.9), 
                          (55,self.histWindowSize[1]*0.9), 2 )
        fontsize = 20
        myfont = pygame.font.SysFont( "None", fontsize )
        self.surf.blit(myfont.render( str(self.maxVal), 0, white), 
                       (15, self.histWindowSize[1]*0.087) )
        self.surf.blit(myfont.render( str(self.maxVal/2), 0, white), 
                       (15, self.histWindowSize[1]/2-5) )
        self.surf.blit(myfont.render("0", 0, white), 
                       (15, self.histWindowSize[1]*0.887) )

        while 1:
            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_q:
                        sys.exit(1)
                
            
            hist = conn.recv()
            for i in range(len(hist)):
                rectHeight = -1 * self.histWindowSize[1]*0.8 * hist[i] / self.maxVal
                blackrect = ( 115+i*50, self.histWindowSize[1]*0.05, 
                              20, self.histWindowSize[1]*0.9 )
                rect = (115+i*50, self.histWindowSize[1]*0.9, 
                        20, rectHeight )
                pygame.draw.rect(self.surf, black, blackrect, 0 )
                pygame.draw.rect(self.surf, self.activePalette[i], rect, 0 )
                pygame.display.update()

    def __init__ ( self, N, maxVal, palette ):
        Histogram.__init__( self, N, maxVal, palette )
        
    def update( self, hist ):
        if len(hist) != self.N:
            print "Not the correct number of elements for the histogram!"
            return
        else:
            self.conn2.send( hist )
    
    def finish( self ):
        self.p.terminate()



class HTickerlines(Histogram):
    def runProcess( self, conn ):
        pygame.init()
        self.histWindowSize = ( 500, 200 )
        self.offsetX = 70
        self.surf = pygame.display.set_mode( (self.histWindowSize[0]+self.offsetX,
                                              self.histWindowSize[1]) )
        pygame.display.set_caption( "HTickerline-Histogram" )
        history = np.zeros( ( self.N, 2 ), int )
        for i in range(self.N):
            history[i] = ( self.offsetX, self.histWindowSize[1]/2)

        posX = 0
        pygame.draw.line( self.surf, white, (50,self.histWindowSize[1]*0.05), 
                          (50,self.histWindowSize[1]*0.95), 2 )
        pygame.draw.line( self.surf, white, (45,self.histWindowSize[1]*0.05), 
                          (55,self.histWindowSize[1]*0.05), 2 )
        pygame.draw.line( self.surf, white, (45,self.histWindowSize[1]/2), 
                          (55,self.histWindowSize[1]/2), 2 )
        pygame.draw.line( self.surf, white, (45,self.histWindowSize[1]*0.95), 
                          (55,self.histWindowSize[1]*0.95), 2 )
        fontsize = 20
        myfont = pygame.font.SysFont( "None", fontsize )
        self.surf.blit(myfont.render( str(self.maxVal), 0, white), (15, 15) )
        self.surf.blit(myfont.render( str(self.maxVal/2), 0, white), 
                       (15,self.histWindowSize[1]/2-5 ) )
        self.surf.blit(myfont.render( "0", 0, white), (15, self.histWindowSize[1]-25) )
        
        showFlags = np.ones( 8, bool )

        while 1:
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
                        sys.exit(1)


            hist = conn.recv()
                    
            if posX % 100 == 0: # (*)
                self.surf.fill( black, (self.offsetX + (posX % self.histWindowSize[0]),
                                        0.05*self.histWindowSize[1], 
                                        0.2 *self.histWindowSize[0],
                                        self.histWindowSize[1]*0.95 ), 0 )
                
            for i in range(len(hist)):
                posY = ( self.histWindowSize[1]*0.95 - 
                         (self.histWindowSize[1]*0.9) * hist[i] / self.maxVal )
                pos = (self.offsetX + posX % self.histWindowSize[0], posY)
                if pos[0] - history[i][0] < 0:
                    history[i][0] = self.offsetX
                if showFlags[i] == True:
                    pygame.draw.line( self.surf, self.activePalette[i], 
                                      history[i], pos, 2 )

                history[i] = pos
                pygame.display.update()
            
            posX += 5 #if you change this, remember (*)

                

    def __init__( self, N, maxVal, palette ):
        Histogram.__init__( self, N, maxVal, palette )

    def update( self, hist ):
        if len(hist) != self.N:
            print "Not the correct number of elements for the histogram!"
            return
        else:
            self.conn2.send( hist )
    


if __name__ == "__main__":
    pygame.init()
    maxi = 1254
    h = HTickerlines( 4, maxi, ())
    v = VBars( 4, maxi, () )
    while 1:
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
        tuple =(j,k,l,m)
        h.update( tuple )
        v.update( tuple )



    
