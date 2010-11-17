import pygame
import numpy as np
from multiprocessing import Process, Pipe, Queue
import Histogram
import sys 
import time
from os import path, getcwd, chdir, listdir, path
import optparse


## class Display() handles everything connected to displaying the configuration of a CA.
#
# It handles zooming, resizing, scrolling, handling 1D and 2D CA, 
# the colors used for different states of a cell, user input like
# file names and displaying short info messages and updating everything over and over again.
class Display():
    ## Constructor, initializes pretty everything
    def __init__( self, size, scale, palette, dim, oneLiner=False ):
        ## Size of the showing CA
        self.size = self.sizeX, self.sizeY = X,Y = size
        ## Factor by which a cell is scaled to show it bigger than one pixel on the screen
        self.scale = scale
        ## Actual size of the simulation window
        self.screenSize = int(self.sizeX*self.scale),int(self.sizeY*self.scale)
        self.palette = palette

        pygame.display.init()
        pygame.display.set_caption( "CASimulator - " )
        pygame.display.set_mode( self.screenSize, 0, 8 )

        ## Pygame display object
        self.simScreen = pygame.display.get_surface()

        ## Clock used to calculate fps rate
        self.clock = pygame.time.Clock()

        # initialize zoomscreenstuff

        ## Index of the first cell displayed on the left
        self.screenXMin = 0
        ## Index of the first cell displayed on the top
        self.screenYMin = 0
        ## Iterator for zoomSize selection (see zoomSizes)
        self.zoomIdx = 0
        ## Fixed number of cells displayed (width, height)
        # e.g.: [(20.0,20.0), (15.0,15,0), ... ]
        self.zoomSizes = []
        self.zoomSizes.append( (float(X), float(Y)) )
        self.zoomSizes.append( (float(X*3/4), float(Y*3/4) ) )
        i = 2
        while self.zoomSizes[len(self.zoomSizes)-1][0] != (X/i) \
                and self.zoomSizes[len(self.zoomSizes)-1][1] != (Y/i):
            self.zoomSizes.append( (float(X/i),float(Y/i)) )
            i += 1

        self.oneLiner = oneLiner
        ## Toplevel pygame surface. All subsurfaces are children of this.
        self.surface = pygame.surface.Surface( self.size, 0, 8 )

        # initialize showText-stuff
        pygame.font.init()
        ## Fontsize used to display messages
        self.myfontSize = 12
        ## Font used to display messages
        self.myfont = pygame.font.SysFont( "dejavuserif", self.myfontSize, True )

        # freemono bold
        # dejavuserif bold
        # mgopenmoderna
        # to get all supported systemfonts:
        # import pygame
        # pygame.font.get_fonts()

        ## Number of iterations of the main loop in Simulator::start() for how
        ## long the messages are kept visible
        self.newTextLive = 50
        ## How many iterations of the main loop left where message is visible
        self.textAlive = self.newTextLive
        ## 'HeadsUpDisplay', the message that is being shown
        self.HUDText = "Start"
        self.filenameChars = ("a", "b", "c", "d", "e", "f", "g", "h", "i", "j", 
                              "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", 
                              "u", "v", "w", "x", "y", "z", "A", "B", "C", "D", 
                              "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", 
                              "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", 
                              "Y", "Z", "0", "1", "2", "3", "4", "5", "6", "7", 
                              "8", "9", "_", "-", "/", "." )
        
        if dim == 1:
            self.counterPos = (0,0)
            self.textPos = (0.5*self.screenSize[0], 0)
        elif dim == 2:
            self.counterPos = (0,self.sizeY*self.scale-1.1*self.myfontSize)
            self.textPos = (0,0)



    ## Get the coordinate of the cell that is clicked on in the display window
    def getCACoordinates( self, clickedCoords ):
        retX = clickedCoords[0] / self.scale
        retY = clickedCoords[1] / self.scale
        retX /= self.sizeX/self.zoomSizes[self.zoomIdx][0]
        retY /= self.sizeY/self.zoomSizes[self.zoomIdx][1]
        retX += self.screenXMin
        retY += self.screenYMin
        return (int(retX),int(retY))

    ## Get the size of the CA being displayed
    def getSize( self ):
        pass

    ## A kind of commandline that is displayed as HUD
    def getUserInputKey( self, msg="$> ", default="", fileHandling=False ):
        self.simScreen.fill( (0,0,0) )
        inStr = default
        self.simScreen.blit( self.myfont.render( msg + ": ", 0,
                                                 (255,255,255), (0,0,0) ),
                             (0,0) )
        while 1:
            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN:
                    mod = pygame.key.get_mods()
                    if e.key == pygame.K_BACKSPACE:
                        # deleting either one or all character(s)
                        if mod & pygame.KMOD_LCTRL:
                            p1 = max(inStr.rfind( ".", 0, -1 )+1,0)
                            p2 = max(inStr.rfind( "_", 0, -1 )+1,0)
                            p = max(p1, p2)
                            inStr = inStr[:p]
                        else:
                            inStr = inStr[0:-1]
                    elif e.key == pygame.K_c and mod & pygame.KMOD_LCTRL:
                        # cancelling input
                        return ""
                    elif e.key == pygame.K_RETURN:
                        # returning input
                        return inStr
                    elif e.key == pygame.K_TAB and fileHandling:
                        # filename-completion
                        dirList = listdir( getcwd() )
                        dirList.sort()
                        files = []
                        for f in dirList:
                            if path.isdir(f) and f[0:1] != "." \
                                    and inStr == f[0:len(inStr)]:
                                files.append(f)
                        for f in dirList:
                            if path.isfile(f) and f[0:1] != "." \
                                    and f[-1:] != "~" and inStr == f[0:len(inStr)]:
                                files.append(f)
                        
                        # find common prefix in files
                        if len(files) > 0:
                            flag = True
                            i = len(inStr)
                            while flag:
                                commonPrefix = files[0][:i+1]
                                for f in files:
                                    flag = flag and len(f) > i and f[:i+1] == commonPrefix
                                if flag:
                                    i += 1
                            inStr = commonPrefix[:-1]
                            
                        if len(files) == 1:
                            inStr = files[0]
                        lineY = 4*int(self.myfontSize*4/3)
                        pygame.draw.rect( self.simScreen, (0,0,0), 
                                          (0, lineY, self.simScreen.get_width(), 
                                           self.simScreen.get_height()-lineY ) )
                        if path.isdir(inStr):
                            chdir( inStr )
                            inStr = ""
                        else:
                            # show directories first
                            for f in files:
                                if path.isdir(f) and f[0:1] != ".":
                                    self.simScreen.blit( self.myfont.render( f, 0,
                                                                             (70,110,255), (0,0,0) ),
                                                         (0,lineY) )
                                else:
                                    self.simScreen.blit( self.myfont.render( f, 0,
                                                                             (127,227,127), (0,0,0) ),
                                                         (0,lineY) )
    
                                lineY += int(self.myfontSize*4/3)
                                if lineY > self.simScreen.get_width()-2*int(self.myfontSize*4/3):
                                    self.simScreen.blit( self.myfont.render( "<q> to quit, <SPACE> to continue...", 0,
                                                                             (255,255,255), (0,0,0) ),
                                                         (0,self.simScreen.get_width()-int(self.myfontSize*4/3)) )
                                    pygame.display.update()
                                    loop = 0
                                    while loop == 0:
                                        for e in pygame.event.get():
                                            if e.type == pygame.KEYDOWN:
                                                if e.unicode == "q":
                                                    loop = 1
                                                if e.key == pygame.K_SPACE:
                                                    loop = 2
                                    if loop == 1:
                                        pygame.draw.rect( self.simScreen, (0,0,0), 
                                                          (0,self.simScreen.get_height()-int(self.myfontSize*4/3), 
                                                           self.simScreen.get_width(), int(self.myfontSize*4/3)) )

                                        break
                                    elif loop == 2:
                                        lineY = 4*int(self.myfontSize*4/3)
                                        pygame.draw.rect( self.simScreen, (0,0,0), 
                                                          (0, lineY, self.simScreen.get_width(), self.simScreen.get_height()-lineY ) )
                                    
                                    
                    elif e.key == pygame.K_PERIOD and fileHandling \
                            and mod & pygame.KMOD_CTRL and mod & pygame.KMOD_SHIFT:
                        chdir( ".." )
                        pygame.draw.rect( self.simScreen, (0,0,0), 
                                          ( (0, 2*int(self.myfontSize*4/3), self.simScreen.get_width(), int(self.myfontSize*4/3) ) ) )
                    elif e.unicode in self.filenameChars:
                        # adding characters to inStr
                        inStr += e.unicode
                pygame.draw.rect( self.simScreen, (0,0,0), 
                                  ( (0,int(self.myfontSize*4/3)),
                                    (self.simScreen.get_width(),int(self.myfontSize*4/3) )))
                self.simScreen.blit( self.myfont.render( inStr, 0,
                                                         (127,227,127), (0,0,0) ),
                                     (0,int(self.myfontSize*4/3)) )
                if fileHandling:
                    self.simScreen.blit( self.myfont.render( "in ", 0,
                                                             (255,255,255), (0,0,0) ),
                                         (0,2*int(self.myfontSize*4/3)) )
                    self.simScreen.blit( self.myfont.render( getcwd(), 0,
                                                             (70,110,255), (0,0,0) ),
                                         (20,2*int(self.myfontSize*4/3)) )
                    self.simScreen.blit( self.myfont.render( "(CTRL-SHIFT-. to go to parent dir)", 0,
                                                             (255,255,255), (0,0,0) ),
                                         (0,3*int(self.myfontSize*4/3)) )
                pygame.display.update()
            
    def quit( self ):
        pass

    ## Setting up text to show a message
    # @param text The message that is going to be displayed
    def setText( self, text ):
        self.HUDText = text
        self.textAlive = self.newTextLive

    ## Display a step counter
    # Counter is displayed at the bottom left corner.
    # It could have been displayed at the top left corner but it would interfere with
    # messages displayed by Display::showText()
    # @param c The stepcount
    def showCounter( self, c ):
        self.simScreen.blit( self.myfont.render( "Step " + str( c ), 
                                                 0, (255,255,255),
                                                 (0,0,0) ), self.counterPos )


    ## Display messages
    # If textAlive > 0, i.e. if the message hasn't been visible for it's maximum
    # time of visibility, the message is being displayed in the top left corner
    def showText( self ):
        if self.textAlive > 0:
            self.textAlive -= 1
            self.simScreen.blit( self.myfont.render( str( self.HUDText ), 0, 
                                                     (255,255,255), 
                                                     (0,0,0) ), self.textPos )

    ## Updating the pygame display, setting window caption
    def update( self ):
        self.clock.tick()
        pygame.display.set_caption( "CASimulator - " 
                                    + str(int(self.clock.get_fps())) + "fps" )
        pygame.display.update()



##################################
## DISPLAYSQUARES - SUPER-CLASS ##
##################################
class DisplaySquares( Display ):
    ## Constructor, initializes pretty everything
    def __init__( self, size, scale, palette, dim, oneLiner=False ):
        Display.__init__( self, size, scale, palette, dim, oneLiner )
        self.palette = palette

        pygame.display.set_palette( palette )
        pygame.display.set_mode( self.screenSize, 0, 8 )

        self.surface.set_palette( palette )

        self.dim = dim


    def drawConf( self, data, running ):
        self.blitArray( data, running )
        

    ## Get the size of the CA being displayed
    def getSize( self ):
        return self.size


    ## Make the display bigger or smaller
    # @param f Factor by which the size is scaled
    def resize( self, f ):
        self.scale *= f
        self.screenSize = int(self.sizeX*self.scale),int(self.sizeY*self.scale)
        pygame.display.set_mode( self.screenSize, 0, 8 )



######################################
## DISPLAYSQUARES - ONE DIMENSIONAL ##
######################################
class DisplaySquares1D( DisplaySquares ):
    ## Constructor, initializes pretty everything
    def __init__( self, size, scale, palette, dim, oneLiner=False ):
        DisplaySquares.__init__( self, size, scale, palette, dim, oneLiner )

        # New configurations of a 1D CA are displayed only in the bottom line
        self.newlineSurface = self.surface.subsurface( (0,self.sizeY-1,self.sizeX,1) )
        self.displaySurface = self.surface.subsurface( (0,
                                                        self.sizeY-self.zoomSizes[self.zoomIdx][1]),
                                                        self.zoomSizes[self.zoomIdx] )

    ## Blitting function used for 1D CA
    def blitArray( self, data, scroll ):
        scroll = (int)(scroll)*(-1)*self.oneLiner
        self.surface.scroll( 0, scroll )

        pygame.surfarray.blit_array( self.newlineSurface, data )
        temp = pygame.transform.scale( self.displaySurface, self.simScreen.get_size() ) 
        self.simScreen.blit( temp, (0,0) )


    ## When zoomed, scrolling to the left and to the right in 1D CA
    # In 1D CA scrolling up and down is not supported yet
    # @param key Pygame.Key object containing the pressed key
    def scroll( self, key ):
        if key == pygame.K_LEFT and self.screenXMin > 0:
            self.screenXMin -= 1
        if key == pygame.K_RIGHT and self.screenXMin + self.zoomSizes[self.zoomIdx][0] < self.sizeX:
            self.screenXMin += 1
        self.displaySurface = self.surface.subsurface( (self.screenXMin, 
                                                        self.sizeY-self.zoomSizes[self.zoomIdx][1]),
                                                       self.zoomSizes[self.zoomIdx] )
            

    ## Zooming into a 1D CA
    # Here the initialized fixed zoomSizes from init() are used
    # @param c User input indicating zooming in or zooming out
    def zoom( self, c ):
        if c == "0":
            self.zoomIdx = 0
        elif c == "1" and self.zoomIdx < len(self.zoomSizes)-1:
            self.zoomIdx += 1
        elif c == "2" and self.zoomIdx > 0:
            self.zoomIdx -= 1
        self.screenXMin = min( self.screenXMin, self.sizeX-self.zoomSizes[self.zoomIdx][0] )
        self.displaySurface = self.surface.subsurface( 
            (self.screenXMin, self.sizeY-self.zoomSizes[self.zoomIdx][1]),
            self.zoomSizes[self.zoomIdx] )

        
######################################
## DISPLAYSQUARES - TWO DIMENSIONAL ##
######################################
class DisplaySquares2D( DisplaySquares ):
    ## Constructor, initializes pretty everything
    def __init__( self, size, scale, palette, dim, oneLiner=False ):
        DisplaySquares.__init__( self, size, scale, palette, dim, oneLiner )
        self.subSurf = self.surface.subsurface( (0,0), self.size)

    ## Blitting function used for 2D CA
    def blitArray( self, data, swap ):
        pygame.surfarray.blit_array( 
            self.subSurf, 
            data[self.screenXMin:self.screenXMin+self.subSurf.get_width(),
                 self.screenYMin:self.screenYMin+self.subSurf.get_height()] )
        temp = pygame.transform.scale( self.subSurf, self.simScreen.get_size() )
        self.simScreen.blit( temp, (0,0) )

            
    def resize( self, f ):
        DisplaySquares.resize( self, f )
        self.counterPos = (0,self.sizeY*self.scale-1.1*self.myfontSize)


    ## When zoomed, scrolling left, right, up and down in 2D CA
    # @param key Pygame.Key object containing the pressed key
    def scroll( self, key ):
        if key == pygame.K_UP and self.screenYMin > 0:
            self.screenYMin -= 1
        elif key == pygame.K_DOWN \
                and self.screenYMin+self.subSurf.get_height() < self.sizeY:
            self.screenYMin += 1
        elif key == pygame.K_LEFT and self.screenXMin > 0:
            self.screenXMin -= 1
        elif key == pygame.K_RIGHT \
                and ( self.screenXMin+self.subSurf.get_width() < self.sizeX ):
            self.screenXMin += 1
            

    ## Zooming into a 2D CA
    # Here the initialized fixed zoomSizes from init() are used
    # @param c User input indicating zooming in or zooming out
    def zoom( self, c ):
        if c == "0":
            self.zoomIdx = 0
        elif c == "1" and self.zoomIdx < len(self.zoomSizes)-1:
            self.zoomIdx += 1
        elif c == "2" and self.zoomIdx > 0:
            self.zoomIdx -= 1
        self.subSurf = self.surface.subsurface( (0,0), 
                                                (int(self.zoomSizes[self.zoomIdx][0]),
                                                 int(self.zoomSizes[self.zoomIdx][1])) )
        self.screenXMin = min( self.screenXMin, self.sizeX-self.zoomSizes[self.zoomIdx][0] )
        self.screenYMin = min( self.screenYMin, self.sizeY-self.zoomSizes[self.zoomIdx][1] )


#################################
## DISPLAYIMAGES - SUPER-CLASS ##
#################################
class DisplayImages( Display ):
    ## Constructor, initializes pretty everything
    def __init__( self, size, scale, palette, dim, oneLiner=False ):
        Display.__init__( self, size, scale, palette, dim, oneLiner )

        ## Actual size of the simulation window
        self.screenSize = int(self.sizeX*self.scale),int(self.sizeY*self.scale)

        self.palette = palette

        pygame.display.set_mode( self.screenSize, 0, 8 )

        ## A quick way to remember whether a 1D or 2D CA is simulated
        self.dim = dim

        self.stateImages = []
        for img in palette:
            self.stateImages.append( pygame.transform.scale(img,(int(scale),int(scale))))
        self.stateImageDict = {}
        self.stateImageDict[(int(scale),int(scale))] = self.stateImages
            

    ## Draws the blitted data to the screen
    def drawConf( self, data, running ):
        self.blitImages( data, running )
        

    ## Get the size of the CA being displayed
    def getSize( self ):
        return self.size


    def rescaleImages( self ):
#        if self.stateImageDict.has_key( size ):
#            self.stateImages = self.stateImageDict[size]
#        else:
        iX = int( self.screenSize[0] / self.zoomSizes[self.zoomIdx][0] )
        iY = int( self.screenSize[1] / self.zoomSizes[self.zoomIdx][1] )
        size = (iX,iY)
        self.stateImages = []
        for img in self.palette:
            self.stateImages.append( pygame.transform.scale( img, size ) )
        #self.stateImageDict[size] = self.stateImages

    ## Make the display bigger or smaller
    # @param f Factor by which the size is scaled
    def resize( self, f ):
        if f > 1:
            self.scale += 1
        elif f < 1:
            self.scale -= 1

        self.screenSize = int(self.sizeX*self.scale),int(self.sizeY*self.scale)
        pygame.display.set_mode( self.screenSize, 0, 8 )

        self.rescaleImages()


#####################################
## DISPLAYIMAGES - ONE DIMENSIONAL ##
#####################################
class DisplayImages1D( DisplayImages ):
    ## Constructor, initializes pretty everything
    def __init__( self, size, scale, palette, dim, oneLiner=False ):
        DisplayImages.__init__( self, size, scale, palette, dim, oneLiner )
        self.newlineSurface = self.simScreen.subsurface( 
            (0,(self.screenSize[1]-self.stateImages[0].get_height()),
             int(self.zoomSizes[self.zoomIdx][0])*self.stateImages[0].get_width(), 
             self.stateImages[0].get_height() ) )

    def blitImages( self, data, scroll ):
        imSizeX = self.stateImages[0].get_width()
        imSizeY = self.stateImages[0].get_height()
        scroll = int((scroll)*(-int( self.screenSize[1] / self.zoomSizes[self.zoomIdx][1] )))*self.oneLiner
        self.simScreen.scroll( 0, scroll )

        for x in range(int(self.zoomSizes[self.zoomIdx][0])):
            self.newlineSurface.blit( self.stateImages[data[self.screenXMin+x]], (x*imSizeX, 0 ) )
        temp = pygame.transform.scale( 
            self.newlineSurface.subsurface(((0,0), 
                                            (int(self.zoomSizes[self.zoomIdx][0]*imSizeX),imSizeY)) ),
            ((self.simScreen.get_width(), int( self.screenSize[1] / self.zoomSizes[self.zoomIdx][1] )) ) )
        self.simScreen.blit( 
            temp, 
            (0,self.simScreen.get_height()-int( self.screenSize[1] / self.zoomSizes[self.zoomIdx][1] )) )


    def resize( self, f ):
        DisplayImages.resize( self, f )
        self.newlineSurface = self.simScreen.subsurface( 
            (0,(self.screenSize[1]-self.stateImages[0].get_height()),
             int(self.zoomSizes[self.zoomIdx][0])*self.stateImages[0].get_width(), 
             self.stateImages[0].get_height() ) )


    ## When zoomed, scrolling to the left and to the right in 1D CA
    # In 1D CA scrolling up and down is not supported yet
    # @param key Pygame.Key object containing the pressed key
    def scroll( self, key ):
        if key == pygame.K_LEFT and self.screenXMin > 0:
            self.screenXMin -= 1
        if key == pygame.K_RIGHT \
                and ( self.screenXMin+self.zoomSizes[self.zoomIdx][0] < self.sizeX ):
            self.screenXMin += 1
            

    ## Zooming into a 1D CA
    # Here the initialized fixed zoomSizes from init() are used
    # @param c User input indicating zooming in or zooming out
    def zoom( self, c ):
        if c == "0":
            self.zoomIdx = 0
        elif c == "1" and self.zoomIdx < len(self.zoomSizes)-1:
            self.zoomIdx += 1
        elif c == "2" and self.zoomIdx > 0:
            self.zoomIdx -= 1
        self.rescaleImages()
        self.newlineSurface = self.simScreen.subsurface( 
            (0,(self.screenSize[1]-self.stateImages[0].get_height()),
             int(self.zoomSizes[self.zoomIdx][0])*self.stateImages[0].get_width(), 
             self.stateImages[0].get_height() ) )
        self.screenXMin = min( self.screenXMin, self.sizeX-self.zoomSizes[self.zoomIdx][0] )

        

#####################################
## DISPLAYIMAGES - TWO DIMENSIONAL ##
#####################################
class DisplayImages2D( DisplayImages ):
    ## Constructor, initializes pretty everything
    def __init__( self, size, scale, palette, dim, oneLiner=False ):
        DisplayImages.__init__( self, size, scale, palette, dim, oneLiner )

        self.subSurf = self.simScreen.subsurface( (0,0), self.screenSize )


    def blitImages( self, data, swap ):
        imgSizeX = self.stateImages[0].get_width()
        imgSizeY = self.stateImages[0].get_height()
        for x in range(int(self.zoomSizes[self.zoomIdx][0])):
            for y in range(int(self.zoomSizes[self.zoomIdx][1])):
                self.subSurf.blit( self.stateImages[data[self.screenXMin+x,self.screenYMin+y]], 
                                   (x*imgSizeX, y*imgSizeY) )

        temp = pygame.transform.scale( 
            self.subSurf.subsurface((0,0), 
                                    (int(self.zoomSizes[self.zoomIdx][0]*imgSizeX), 
                                     int(self.zoomSizes[self.zoomIdx][1]*imgSizeY)) ), 
            self.simScreen.get_size() )
        self.simScreen.blit( temp, (0,0) )


    def resize( self, f ):
        DisplayImages.resize( self, f )
        self.subSurf = self.simScreen.subsurface( (0,0), self.screenSize )
        self.counterPos = (0,self.sizeY*self.scale-1.1*self.myfontSize)


    ## When zoomed, scrolling left, right, up and down in 2D CA
    # @param key Pygame.Key object containing the pressed key
    def scroll( self, key ):
        if key == pygame.K_UP:
            if self.screenYMin > 0:
                self.screenYMin -= 1
        elif key == pygame.K_DOWN \
                and self.screenYMin+self.zoomSizes[self.zoomIdx][1] < self.sizeY:
            self.screenYMin += 1
        elif key == pygame.K_LEFT and self.screenXMin > 0:
            self.screenXMin -= 1
        elif key == pygame.K_RIGHT \
                and ( self.screenXMin+self.zoomSizes[self.zoomIdx][0] < self.sizeX ):
            self.screenXMin += 1


    ## Zooming into a 2D CA
    # Here the initialized fixed zoomSizes from init() are used
    # @param c User input indicating zooming in or zooming out
    def zoom( self, c ):
        if c == "0":
            self.zoomIdx = 0
        elif c == "1" and self.zoomIdx < len(self.zoomSizes)-1:
            self.zoomIdx += 1
        elif c == "2" and self.zoomIdx > 0:
            self.zoomIdx -= 1
        iX = int( self.screenSize[0] / self.zoomSizes[self.zoomIdx][0] )
        iY = int( self.screenSize[1] / self.zoomSizes[self.zoomIdx][1] )
        self.rescaleImages()
        self.screenXMin = min( self.screenXMin, self.sizeX-self.zoomSizes[self.zoomIdx][0] )
        self.screenYMin = min( self.screenYMin, self.sizeY-self.zoomSizes[self.zoomIdx][1] )

