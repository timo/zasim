#!/usr/bin/python

## @package sim.py
# 
# sim.py is the central simulating unit.
# It handles displaying the simulated CA as well as userinput.


CASimulatorHelp = """

**********************
*    CASimulator     *
**********************

Help
~~~~
Mouseclicks:
  leftclick       Sandpile: Add a grain
  rightclick      Sandpile: Set state to 0
Display:
  '+'             Scale up the window
  '-'             Scale down the window
  '0'             Set zoom to 1:1
  '1'             Zoom in
  '2'             Zoom out
  'c'             Toggle display of step counter
  ('f'            Toggle full screen DONT USE THIS)
Cursor (when zoomed in)
  left            Move view left
  right                     right
  up                        up
  down                      down
Simulation:
  '*'             Bigger delay
  '/'             Smaller delay
  '='             No delay
  'm'             Mark configuration
  's'             Do only one step and stop
  SPACE           Start/Stop the simulation
  TAB             Load next marked configuration
  SHIFT-TAB       Load previous marked configuration
  CTRL-TAB        Kill current marked configuration from buffer
  CTRL-SHIFT-TAB  Set a name for the most recently marked configuration
  CTRL-s          Save currently shown configuration to file
  CTRL-o          Open configuration from file
  'h'             Print this help
  'q'             Quit


"""


import pygame
import numpy as np
from multiprocessing import Process, Pipe, Queue
from CA import sandpile, catpile, binRule, bigFish
import Histogram
import sys 
import time
from os import path
import optparse

## class Display() handles everything connected to displaying the configuration of a CA.
#
# It handles zooming, resizing, scrolling, handling 1D and 2D CA, 
# the colors used for different states of a cell, user input like
# file names and displaying short info messages and updating everything over and over again.
class Display():
    ## Constructor, initializes pretty everything
    def __init__( self, size, scale, palette, CADisplayType, dim ):
        ## Size of the showing CA
        self.size = self.sizeX, self.sizeY = X,Y = size
        ## Factor by which a cell is scaled to show it bigger than one pixel on the screen
        self.scale = scale
        ## Actual size of the simulation window
        self.screenSize = int(self.sizeX*self.scale),int(self.sizeY*self.scale)
        self.CADisplayType = CADisplayType
        self.palette = palette

        pygame.display.init()
        pygame.display.set_caption( "CASimulator - " )
        pygame.display.set_mode( self.screenSize, 0, 8 )
        if CADisplayType == "Squares":
            pygame.display.set_palette( palette )
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
        ## Fixed zoom factors when zooming into the CA to view only a detail
        self.zoomSizes = []
        self.zoomSizes.append( (float(X), float(Y)) )
        self.zoomSizes.append( (float(X*3/4), float(Y*3/4) ) )
        i = 2
        while self.zoomSizes[len(self.zoomSizes)-1][0] != (X/i) \
                and self.zoomSizes[len(self.zoomSizes)-1][1] != (Y/i):
            self.zoomSizes.append( (float(X/i),float(Y/i)) )
            i += 1

        ## Toplevel pygame surface. All subsurfaces are children of this.
        self.surface = pygame.surface.Surface( self.size, 0, 8 )
        if CADisplayType == "Squares":
            self.surface.set_palette( palette )

        if CADisplayType == "Images":
            self.subSurf = self.surface.subsurface( (0,0), self.surface.get_size() )
        elif CADisplayType == "Squares":
            # subSurf is the surface where the unscaled 1x1-pixel-squares for each state
            # are blitted to. Afterwards subSurf is scaled up to simScreenSize
            self.subSurf = self.surface.subsurface( (0,0), self.size )

        ## A quick way to remember whether a 1D or 2D CA is simulated
        self.dim = dim
        if self.dim == 1:
            ## New configurations of a 1D CA are displayed only in the bottom line
            self.newlineSurface = self.surface.subsurface( (0,Y-1,X,1) )
            ## Temporary array needed for blitting the conf of a 1D CA (see blitArray1D)
            self.array = np.zeros( (1,X), int )
            if CADisplayType == "Squares":
                self.blitArray = self.blitArray1D
            elif CADisplayType == "Images":
                self.blitArray = self.blitImage1D
                self.stateImages = []
                for img in palette:
                    self.stateImages.append( pygame.transform.scale( img, (scale,scale) ) )
            else:
                print "Wrong 1D-Displaytype found!"
                sys.exit(1)
            self.scroll = self.scroll1D
            self.zoom = self.zoom1D
        elif self.dim == 2:
            if CADisplayType == "Squares":
                self.blitArray = self.blitArray2D
            elif CADisplayType == "Images":
                self.blitArray = self.blitImage2D
                self.stateImages = []
                for img in palette:
                    self.stateImages.append( pygame.transform.scale( img, (int(scale),int(scale)) ) )
            else:
                print "Wrong 2D-Displaytype found!"
                sys.exit(1)
            self.scroll = self.scroll2D
            self.zoom = self.zoom2D
        else:
            print "There is no function Display.blitArray() for dim =", self.dim
            sys.exit(1)

        # initialize showText-stuff
        pygame.font.init()
        ## Fontsize used to display messages
        self.myfontSize = 15
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


    ## Blitting function used for 1D CA
    def blitArray1D( self, data, scroll ):
        scroll = (int)(scroll)*(-1)
        self.surface.scroll( 0, scroll )

        if self.screenXMin + self.subSurf.get_width() > self.sizeX:
            self.screenXMin = self.sizeX - self.subSurf.get_width()

        pygame.surfarray.blit_array( 
            self.newlineSurface,                                      
            data[self.screenXMin:self.screenXMin+self.subSurf.get_width(),:] )
        temp = pygame.transform.scale( self.subSurf, self.simScreen.get_size() )
        self.simScreen.blit( temp, (0,0) )
        
    ## Blitting function used for 2D CA
    def blitArray2D( self, data, swap ):
        if self.screenXMin + self.subSurf.get_width() > self.sizeX \
                or self.screenYMin + self.subSurf.get_height() > self.sizeY:
            self.screenXMin = self.sizeX-self.subSurf.get_width()
            self.screenYMin = self.sizeY-self.subSurf.get_height()
        pygame.surfarray.blit_array( 
            self.subSurf, 
            data[self.screenXMin:self.screenXMin+self.subSurf.get_width(),
                 self.screenYMin:self.screenYMin+self.subSurf.get_height()] )
        temp = pygame.transform.scale( self.subSurf, self.simScreen.get_size() )
        self.simScreen.blit( temp, (0,0) )

    def blitImage1D( self, data, swap ):
        pass

    def blitImage2D( self, data, swap ):
        if self.screenXMin + self.subSurf.get_width() > self.sizeX \
                or self.screenYMin + self.subSurf.get_height() > self.sizeY:
            self.screenXMin = self.sizeX-self.subSurf.get_width()
            self.screenYMin = self.sizeY-self.subSurf.get_height()

        for x in range( self.screenXMin, self.screenXMin+int(self.zoomSizes[self.zoomIdx][0]) ):
            for y in range( self.screenYMin, self.screenYMin+int(self.zoomSizes[self.zoomIdx][1]) ):
                self.subSurf.blit( self.stateImages[data[x,y]], (x*self.scale,y*self.scale) )
#        self.simScreen.blit( self.subSurf, (0,0))


#int(self.zoomSizes[self.zoomIdx][0]),int(self.zoomSizes[self.zoomIdx][1])) 

    ## Draws the blitted data to the screen
    def drawConf( self, data, running ):
        self.blitArray( data, running )
        
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
        return self.size

    ## A kind of commandline that is displayed as HUD
    def getUserInputKey( self, msg="$> ", default="" ):
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
                            inStr = "Conf_Rule110_20x20_1.cnf"
#                            inStr = "Conf_Sandpile_20x20_3.cnf"
#                            if inStr[0:5] == "Conf_":
#                                inStr = "Conf_"
                        else:
                            inStr = inStr[0:-1]
                    elif e.key == pygame.K_c and mod & pygame.KMOD_LCTRL:
                        # cancelling input
                        return ""
                    elif e.key == pygame.K_RETURN:
                        # returning input
                        return inStr
                    elif e.key == pygame.K_TAB:
                        # filename-completion
                        #TODO!!!
                        print "TODO: tabs in Display.getUserInputKey()"
                    elif e.unicode in self.filenameChars:
                        # adding characters to inStr
                        inStr += e.unicode
                pygame.draw.rect( self.simScreen, (0,0,0), 
                                  ( (0,self.myfontSize), 
                                    (self.simScreen.get_width(),self.myfontSize )))
                self.simScreen.blit( self.myfont.render( inStr, 0,
                                                         (255,255,255), (0,0,0) ),
                                     (0,self.myfontSize) )
                pygame.display.update()
            
    def quit( self ):
        pass

    ## Make the display bigger or smaller
    # @param f Factor by which the size is scaled
    def resize( self, f ):
        self.scale *= f
        self.screenSize = int(self.sizeX*self.scale),int(self.sizeY*self.scale)
        if self.CADisplayType == "Images":
            self.stateImages = []
            for img in self.palette:
                self.stateImages.append( pygame.transform.scale( img, (int(self.scale),int(self.scale)) ) )
        pygame.display.set_mode( self.screenSize, 0, 8 )
        
    ## When zoomed, scrolling to the left and to the right in 1D CA
    # In 1D CA scrolling up and down is not supported yet
    # @param key Pygame.Key object containing the pressed key
    def scroll1D( self, key ):
        if key == pygame.K_LEFT and self.screenXMin > 0:
            self.screenXMin -= 1
        if key == pygame.K_RIGHT \
                and ( self.screenXMin+self.subSurf.get_width() < self.sizeX ):
            self.screenXMin += 1
            
    ## When zoomed, scrolling left, right, up and down in 2D CA
    # @param key Pygame.Key object containing the pressed key
    def scroll2D( self, key ):
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
                                                 (0,0,0) ), 
                             (0,self.sizeY*self.scale-1.5*self.myfontSize) )

    ## Display messages
    # If textAlive > 0, i.e. if the message hasn't been visible for it's maximum
    # time of visibility, the message is being displayed in the top left corner
    def showText( self ):
        if self.textAlive > 0:
            self.textAlive -= 1
            self.simScreen.blit( self.myfont.render( str( self.HUDText ), 0, 
                                                     (255,255,255), 
                                                     (0,0,0) ),
                                 (0,0) )

    ## Updating the pygame display, setting window caption
    def update( self ):
        self.clock.tick()
        pygame.display.set_caption( "CASimulator - " 
                                    + str(int(self.clock.get_fps())) + "fps" )
        pygame.display.update()

    ## Zooming into a 1D CA
    # Here the initialized fixed zoomSizes from init() are used
    # @param c User input indicating zooming in or zooming out
    def zoom1D( self, c ):
        if c == "0":
            self.zoomIdx = 0
        elif c == "1" and self.zoomIdx < len(self.zoomSizes)-1:
            self.zoomIdx += 1
        elif c == "2" and self.zoomIdx > 0:
            self.zoomIdx -= 1
        # BUGGY!!!!!
        self.newlineSurface = self.surface.subsurface( (0,0), (int(self.zoomSizes[self.zoomIdx][0]),int(self.zoomSizes[self.zoomIdx][1])) )

    ## Zooming into a 2D CA
    # Here the initialized fixed zoomSizes from init() are used
    # @param c User input indicating zooming in or zooming out
    def zoom2D( self, c ):
        if c == "0":
            self.zoomIdx = 0
        elif c == "1" and self.zoomIdx < len(self.zoomSizes)-1:
            self.zoomIdx += 1
        elif c == "2" and self.zoomIdx > 0:
            self.zoomIdx -= 1
        self.subSurf = self.surface.subsurface( (0,0), (int(self.zoomSizes[self.zoomIdx][0]),int(self.zoomSizes[self.zoomIdx][1])) )
        

class Simulator():
    def __init__( self, CAType, confFile, random, sizeX, sizeY ):
        if CAType.upper() == "SANDPILE":
            if random:
                self.ca = sandpile( sizeX, sizeY, sandpile.INIT_RAND )
            else:
                self.ca = sandpile( sizeX, sizeY, sandpile.INIT_ZERO )
                if confFile != "":
                    self.ca.importConf( confFile )

        elif CAType[0:7].upper() == "BINRULE":
            self.ca = binRule( int(CAType[7:-1]), sizeX, sizeY, binRule.INIT_RAND )

        elif CAType.upper() == "BIGFISH":
            self.ca = bigFish( sizeX, sizeY )

#        self.ca = catpile( 100, 100, sandpile.INIT_ZERO )

        self.histograms = []
#        self.histograms.append( Histogram.VBars( 8, 1600, self.ca.palette, self.ca.info ) )

        self.display = Display( self.ca.getSize(), 20.0,
                                self.ca.palette,
                                self.ca.getDisplayType(),
                                self.ca.getDim() )
        self.markedConfs = []
        self.markedConfNames = []
        self.delayGranularity = 3
        self.currDelay = 0

    def start( self ):
        loop = False
        delay = 0
        showStepCount = True
        stepCounter = 0
        markedConfIdx = 0
        self.markedConfs.append( self.ca.getConf().copy() )
        self.markedConfNames.append( "init" )
        pygame.key.set_repeat( 700, 100 )
        while 1:
            # note:
            # Modifier like CTRL, SHIFT and ALT only work with conditions
            # like 'if e.key == pygame.K_q', NOT with 
            # 'if e.unicode == "s"'. That shouldn't be a problem with characters,
            # but more special keys like + and = dont work on all machines using
            # pygame.K_PLUS etc (at least not out of the box).
            #

            # pygame-events
            for e in pygame.event.get():
                if e.type == pygame.MOUSEBUTTONDOWN:
                    ev = pygame.event.Event( pygame.MOUSEBUTTONDOWN, 
                                             pos=self.display.getCACoordinates(e.pos),
                                             button=e.button )
                    self.ca.eventFunc( ev )

                if e.type == pygame.KEYDOWN:
                    if e.unicode == "+":
                        self.display.resize(1.1)

                    elif e.unicode == "-":
                        self.display.resize(0.9)
                        
                    elif e.unicode == "*":
                        self.currDelay += self.delayGranularity
                        self.display.setText( "Delay: " + str(self.currDelay) )
                            
                    elif e.unicode == "/":
                        if self.currDelay == 0:
                            self.display.setText( "No delay" )
                        else:
                            self.currDelay -= self.delayGranularity
                            self.display.setText( "Delay: " + str(self.currDelay) )

                    elif e.unicode == "=":
                        self.currDelay = 0
                        self.display.setText( "No delay" )

                    elif e.unicode == "0" or e.unicode == "1" or e.unicode == "2":
                        self.display.zoom( e.unicode )
                        msg = "Zoom: "
                        s = self.display.zoomSizes[self.display.zoomIdx][0]
                        s = (float)(self.display.sizeX)/(float)(s)
                        msg += str(s)
                        self.display.setText( msg )

                    elif e.unicode == "c":
                        showStepCount = not showStepCount

                    # dont use fullscreen, it's buggy, kills your X-Resolution...:(
                    # elif e.unicode == "f":
                    #     pygame.display.toggle_fullscreen()

                        
                    elif e.unicode == "h":
                        print CASimulatorHelp

                    elif e.unicode == "m":
                        self.display.setText( "Marked configuration " + 
                                              str(len(self.markedConfs)) )
                        self.markedConfs.append( self.ca.getConf().copy() )
                        confName = self.display.getUserInputKey(
                            msg="Set name for marked conf:", default="" )
                        self.markedConfNames.append( confName )
                        loop = False
                        
                    elif e.key == pygame.K_o:
                        # stop stepping
                        loop = False
                        
                        mod = pygame.key.get_mods()
                        if mod & pygame.KMOD_LCTRL:
                            # open conffile
                            # filename is generated automatically, but has to be 
                            # acknowledged by the user and can be changed
                            # filenames look like this: Conf_Sandpile_20x20_1.cnf
                            size = self.ca.getSize()
                            sizeStr = str(size[0]) + "x" + str(size[1])
                            fileDescr = "Conf_" + self.ca.getTitle() + "_" + sizeStr
                            i = 0
                            filename = fileDescr + "_" + str(i+1) + ".cnf"
                            while path.exists( filename ):
                                i += 1
                                filename = fileDescr + "_" + str(i+1) + ".cnf"

                            if ( i > 0 ):
                                filename = fileDescr + "_" + str(i) + ".cnf"
                            else:
                                filename = "Conf_<Title>_<SizeX>x<SizeY>_<Number>.cnf"
                            
                            #presenting the user with suggested filename
                            filename = self.display.getUserInputKey( 
                                msg="Open conf from file", default=filename )
                            while not path.exists( filename ):
                                self.display.setText( "File does not exist" )
                                time.sleep( 1 )
                                filename = self.display.getUserInputKey( 
                                    msg="Open conf from file", default=filename )
                                if filename == "":
                                    break
                            if ( filename != "" and
                                 filename != "Conf_<Title>_<SizeX>x<SizeY>_<Number>.cnf" ):
                                    
                                ret = self.ca.importConf( filename )
                                if ret == self.ca.IMPORTOK:
                                    self.display.setText( "Opened file" + filename )
                                elif ret == self.ca.SIZECHANGED:
#                                    print self.ca.getSize()
                                    self.display.__init__( self.ca.getSize(), 
                                                           self.display.scale, 
                                                           self.ca.palette, 
                                                           self.ca.getDisplayType(),
                                                           self.display.dim )
                                elif ret == self.ca.WRONGCA:
                                    print "WRONGCA"
                                    sys.exit(1)
                                    pass
                                elif ret == self.ca.IMPORTNOTOK:
                                    print "IMPORTNOTOK"
                                    sys.exit(1)
                                    pass
                            else:
                                self.display.setText( "Cancelled" )

                    elif e.unicode == "q":
                        sys.exit(1)
                        
                    elif e.unicode == "r":
                        self.display.setText( "Resetting step counter from " + str( stepCounter) )
                        stepCounter = 0


                    elif e.key == pygame.K_s:
                        # first of all: stop stepping
                        loop = False

                        mod = pygame.key.get_mods()
                        if mod & pygame.KMOD_LCTRL:
                            # save conffile
                            # filename is generated automatically, but has to be 
                            # acknowledged by the user and can be changed
                            # filenames look like this: Conf_Sandpile_20x20_1.cnf
                            size = self.ca.getSize()
                            sizeStr = str(size[0]) + "x" + str(size[1])
                            fileDescr = "Conf_" + self.ca.getTitle() + "_" + sizeStr
                            i = 1
                            filename = fileDescr + "_" + str(i) + ".cnf"
                            while path.exists( filename ):
                                i += 1
                                filename = fileDescr + "_" + str(i) + ".cnf"
                            
                            #presenting the user with suggested filename
                            filename = self.display.getUserInputKey( 
                                msg="Save conf to file", default=filename )

                            if filename != "":
                                self.ca.exportConf( filename )
                                self.display.setText( "Saved to " + filename )
                                #while path.exists( filename ) or filename == "":
                                #    display.setText( "File exists! Overwrite? [n/y]" )
                                #    e = pygame.event.get()
                                #    if e.type == pygame.KEYDOWN:
                                #        if e.unicode == "y":
                                #        elif e.unicode == "n":
                                #            filename = self.display.getUserInputKey( 
                                #                msg="Save conf to file", default=filename )
                            else:
                                self.display.setText( "Cancelled" )

                        else:
                            self.ca.step()
                            self.display.drawConf( self.ca.getConf(), True )
                            self.display.setText( "Step" )

                    elif e.key == pygame.K_RIGHT or e.key == pygame.K_LEFT \
                            or e.key == pygame.K_UP or e.key == pygame.K_DOWN:
                        self.display.scroll( e.key )

                    elif e.key == pygame.K_SPACE:
                        loop = not(loop)
                        msg = "Stop"
                        if loop: 
                            msg = "Start"
                        self.display.setText( msg )
                        
                    elif e.key == pygame.K_TAB:
                        loop = False
                        mod = pygame.key.get_mods()
                        if mod & pygame.KMOD_LCTRL and mod & pygame.KMOD_SHIFT:
                            confName = self.display.getUserInputKey(
                                msg = "Name this conf:", default=self.markedConfNames[markedConfIdx] )
                            if confName != "":
                                self.markedConfNames[markedConfIdx] = confName
                        elif mod & pygame.KMOD_SHIFT:
                            markedConfIdx=(markedConfIdx-1)%len(self.markedConfs)
                            if self.markedConfNames[markedConfIdx] == "":
                                self.display.setText( "Load marked conf " 
                                                      + str(markedConfIdx) )
                            else:
                                self.display.setText( "Load marked conf " 
                                                      + self.markedConfNames[markedConfIdx] )
                            self.ca.setConf( self.markedConfs[markedConfIdx] )
                            confChanged = False
                        elif mod & pygame.KMOD_LCTRL:
                            if len(self.markedConfs) > 1 and not confChanged:
                                self.markedConfs.pop(markedConfIdx)
                                self.markedConfNames.pop(markedConfIdx)
                                self.display.setText( "Kill conf " 
                                                     + str(markedConfIdx) )
                                markedConfIdx=(markedConfIdx-1)%len(self.markedConfs)
                        else:
                            markedConfIdx=(markedConfIdx+1)%len(self.markedConfs)
                            if self.markedConfNames[markedConfIdx] == "":
                                self.display.setText( "Load marked conf " 
                                                      + str(markedConfIdx) )
                            else:
                                self.display.setText( "Load marked conf " 
                                                      + self.markedConfNames[markedConfIdx] )
                            self.ca.setConf( self.markedConfs[markedConfIdx] )
                            confChanged = False
                        if self.ca.getSize() != self.display.getSize():
#                            print "not same size:", self.ca.getSize(), self.display.getSize()
                            self.display.__init__( self.ca.getSize(), 
                                                   self.display.scale, 
                                                   self.ca.palette, 
                                                   self.ca.getDisplayType(),
                                                   self.display.dim )

            
            if not globalEventQueue.empty():
                for e in globalEventQueue.get():
                    print e
            
            if loop:
                if self.currDelay > 0:
                    if delay % self.currDelay == 0:
                        self.step(1)
                        stepCounter += 1
                else:
                    self.step(1)
                    stepCounter += 1
            delay += 1

            self.display.drawConf( self.ca.getConf(), loop )
            self.display.showText()
            if showStepCount:
                self.display.showCounter( stepCounter )
            self.display.update()

    def step( self, n ):
        self.ca.loopFunc()
        self.display.update()

    def stop( self ):
        pass

def sim( CAType, confFile, random, sizeX, sizeY):
    simulator = Simulator( CAType, confFile, random, sizeX, sizeY )
    simulator.start()


### user interface functions ###
def start():
    print "starting simulation"
    globalEventQueue.put( "start" )

def stop():
    print "stopping simulation"
    globalEventQueue.put( "stop" )

def step():
    print "doing one step"
    globalEventQueue.put( "step" )

def quit():
    print "sending quit-message to everyone"
    globalEventQueue.put( "quit" )
    simProc.join()
    print "exiting..."
    sys.exit(0)


def listCA():
    print "Available CAs: Sandpile, Binrule"
    sys.exit(0)

if __name__ == "__main__":
    # this Queue should be known to all subsequent processes...
    globalEventQueue = Queue()

    parser = optparse.OptionParser(version = "CASimulator 0.1")
    parser.add_option( "-f", "--file", default="", dest="confFile", help="Load initial configuration from FILE" )
    parser.add_option( "-l", "--list", action="store_true", default=False, dest="listCA", help="List types of supported CA" )
    parser.add_option( "-r", "--random", action="store_true", default=False, dest="random", help="Set initial configuration to RANDOM" )
    parser.add_option( "-t", "--type",  default="Sandpile", dest="CAType", help="Set type of CA (e.g. 'Sandpile' or 'Binrule110')" )
    parser.add_option( "-x", "--sizeX", default=20, dest="sizeX", help="width of CA", type=int )
    parser.add_option( "-y", "--sizeY", default=20, dest="sizeY", help="height of CA", type=int )  
    (options, args) = parser.parse_args()

    if options.listCA:
        listCA()
    if options.CAType[0:7].upper() == "BINRULE":
        try:
            binruleNumber = int(options.CAType[7:])
        except ValueError:
            print "You didn't set a correct binrule number"
            sys.exit(1)
        if not( 0 <= binruleNumber < 256):
            print "The binrule number has to be in [0,255]"
            sys.exit(0)
    

    simProc = Process( target=sim, args=( options.CAType, 
                                          options.confFile, 
                                          options.random,
                                          options.sizeX,
                                          options.sizeY) )
    simProc.start()

