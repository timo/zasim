#!/usr/bin/python

CASimulatorHelp = """

**********************
*    CASimulator     *
**********************

Help
~~~~
Mouseclicks:
  leftclick   Sandpile: Add a grain
  rightclick  Sandpile: Set state to 0
Display:
  '+'         Scale up the window
  '-'         Scale down the window
  '0'         Set zoom to 1:1
  '1'         Zoom in
  '2'         Zoom out
  'c'         Toggle display of step counter
  ('f'        Toggle full screen DONT USE THIS)
Cursor (when zoomed in)
  left        Move view left
  right                 right
  up                    up
  down                  down
Simulation:
  '*'          Bigger delay
  '/'          Smaller delay
  '='          No delay
  'm'          Mark configuration
  's'          Do only one step and stop
  SPACE        Start/Stop the simulation
  TAB          Load next marked configuration
  SHIFT-TAB    Load previous marked configuration
  CTRL-TAB     Kill current marked configuration from buffer
  CTRL-s       Save currently shown configuration to file
  CTRL-o       Open configuration from file
  'h'          Print this help
  'q'          Quit


"""


import pygame
import numpy as np
from multiprocessing import Process, Pipe, Queue
from CA import sandpile, catpile, binRule
import Histogram
import sys 
import time
from os import path

class Display():
    def __init__( self, size, scale, palette, dim ):
        self.size = self.sizeX, self.sizeY = X,Y = size
        self.scale = scale
        self.screenSize = int(self.sizeX*self.scale),int(self.sizeY*self.scale)

        pygame.display.init()
        pygame.display.set_caption( "CASimulator - " )
        pygame.display.set_mode( self.screenSize, 0, 8 )
        pygame.display.set_palette( palette )
        pygame.display.set_mode( self.screenSize, 0, 8 )
        self.simScreen = pygame.display.get_surface()

        self.clock = pygame.time.Clock()

        # initialize zoomscreenstuff
        self.screenXMin = 0
        self.screenYMin = 0
        self.zoomIdx = 0
        self.zoomSizes = []
        self.zoomSizes.append( (float(X), float(Y)) )
        self.zoomSizes.append( (float(X*3/4), float(Y*3/4) ) )
        i = 2
        while self.zoomSizes[len(self.zoomSizes)-1][0] != (X/i) \
                and self.zoomSizes[len(self.zoomSizes)-1][1] != (Y/i):
            self.zoomSizes.append( (float(X/i),float(Y/i)) )
            i += 1

        self.surface = pygame.surface.Surface( self.size, 0, 8 )
        self.surface.set_palette( palette )
        self.subSurf = self.surface.subsurface( (0,0), self.size )

        self.dim = dim
        if self.dim == 1:
#            print "newinit:", X, Y
            self.newlineSurface = self.surface.subsurface( (0,Y-1,X,1) )
            self.array = np.zeros( (1,X), int )
            self.blitArray = self.blitArray1D
            self.scroll = self.scroll1D
            self.zoom = self.zoom1D
        elif self.dim == 2:
            self.blitArray = self.blitArray2D
            self.scroll = self.scroll2D
            self.zoom = self.zoom2D
        else:
            print "There is no function Display.blitArray() for dim =", self.dim
            sys.exit(1)

        # initialize showText-stuff
        pygame.font.init()
        self.myfontSize = 20
        self.myfont = pygame.font.SysFont( "None", self.myfontSize )
        self.newTextLive = 50
        self.textAlive = self.newTextLive
        self.HUDText = "Start"
        self.filenameChars = ("a", "b", "c", "d", "e", "f", "g", "h", "i", "j", 
                              "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", 
                              "u", "v", "w", "x", "y", "z", "A", "B", "C", "D", 
                              "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", 
                              "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", 
                              "Y", "Z", "0", "1", "2", "3", "4", "5", "6", "7", 
                              "8", "9", "_", "-", "/", "." )

                                                
    def blitArray1D( self, data, scroll ):
        scroll = (int)(scroll)*(-1)
        self.surface.scroll( 0, scroll )

        if self.screenXMin + self.subSurf.get_width() > self.sizeX:
            self.screenXMin = self.sizeX - self.subSurf.get_width()

        pygame.surfarray.blit_array( 
            self.newlineSurface,                                      
            data[self.screenXMin:self.screenXMin+self.subSurf.get_width(),:] )
        
    def blitArray2D( self, data, swap ):
        if self.screenXMin + self.subSurf.get_width() > self.sizeX \
                or self.screenYMin + self.subSurf.get_height() > self.sizeY:
            self.screenXMin = self.sizeX-self.subSurf.get_width()
            self.screenYMin = self.sizeY-self.subSurf.get_height()
        pygame.surfarray.blit_array( 
            self.subSurf, 
            data[self.screenXMin:self.screenXMin+self.subSurf.get_width(),
                 self.screenYMin:self.screenYMin+self.subSurf.get_height()] )
        
    def drawConf( self, data, running ):
        self.blitArray( data, running )
        temp = pygame.transform.scale( self.subSurf, self.simScreen.get_size() )
        self.simScreen.blit( temp, (0,0) )
        
    def getCACoordinates( self, clickedCoords ):
        retX = clickedCoords[0] / self.scale
        retY = clickedCoords[1] / self.scale
        retX /= self.sizeX/self.zoomSizes[self.zoomIdx][0]
        retY /= self.sizeY/self.zoomSizes[self.zoomIdx][1]
        retX += self.screenXMin
        retY += self.screenYMin
        return (int(retX),int(retY))

    def getSize( self ):
        return self.size

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

    def resize( self, f ):
        self.scale *= f
        self.screenSize = int(self.sizeX*self.scale),int(self.sizeY*self.scale)
        pygame.display.set_mode( self.screenSize, 0, 8 )
        
    def scroll1D( self, key ):
        if key == pygame.K_LEFT and self.screenXMin > 0:
            self.screenXMin -= 1
        if key == pygame.K_RIGHT \
                and ( self.screenXMin+self.subSurf.get_width() < self.sizeX ):
            self.screenXMin += 1
            
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
            
    def setText( self, text ):
        self.HUDText = text
        self.textAlive = self.newTextLive

    def showCounter( self, c ):
        self.simScreen.blit( self.myfont.render( "Step " + str( c ), 
                                                 0, (255,255,255),
                                                 (0,0,0) ), 
                             (0,5+self.sizeY*self.scale-self.myfontSize) )

    def showText( self ):
        if self.textAlive > 0:
            self.textAlive -= 1
            self.simScreen.blit( self.myfont.render( str( self.HUDText ), 0, 
                                                     (255,255,255), 
                                                     (0,0,0) ),
                                 (0,0) )

    def update( self ):
        self.clock.tick()
        pygame.display.set_caption( "CASimulator - " 
                                    + str(int(self.clock.get_fps())) + "fps" )
        pygame.display.update()

    def zoom1D( self, c ):
        if c == "0":
            self.zoomIdx = 0
        elif c == "1" and self.zoomIdx < len(self.zoomSizes)-1:
            self.zoomIdx += 1
        elif c == "2" and self.zoomIdx > 0:
            self.zoomIdx -= 1
        self.newlineSurface = self.surface.subsurface( (0,0), (int(self.zoomSizes[self.zoomIdx][0]),int(self.zoomSizes[self.zoomIdx][1])) )
#elf.surface.subsurface( (0,Y-1,X,1) )
    def zoom2D( self, c ):
        if c == "0":
            self.zoomIdx = 0
        elif c == "1" and self.zoomIdx < len(self.zoomSizes)-1:
            self.zoomIdx += 1
        elif c == "2" and self.zoomIdx > 0:
            self.zoomIdx -= 1
        self.subSurf = self.surface.subsurface( (0,0), (int(self.zoomSizes[self.zoomIdx][0]),int(self.zoomSizes[self.zoomIdx][1])) )
        

class Simulator():
    def __init__( self ):
        self.ca = binRule( 110, 30, 30, binRule.INIT_RAND )
#        self.ca = sandpile( 30,30, sandpile.INIT_ZERO )
#        self.ca = catpile( 100, 100, sandpile.INIT_ZERO )

        self.histograms = []
#        self.histograms.append( Histogram.VBars( 8, 1600, self.ca.palette, self.ca.info ) )

        self.display = Display( self.ca.getSize(), 20.0,
                                self.ca.palette,
                                self.ca.getDim() )
        self.markedConfs = []
        self.delayGranularity = 3
        self.currDelay = 0

    def start( self ):
        loop = False
        delay = 0
        showStepCount = True
        stepCounter = 0
        markedConfIdx = 0
        self.markedConfs.append( self.ca.getConf().copy() )
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
                        if mod & pygame.KMOD_SHIFT:
                            markedConfIdx=(markedConfIdx-1)%len(self.markedConfs)
                            self.display.setText( "Load marked conf " 
                                                  + str(markedConfIdx) )
                            self.ca.setConf( self.markedConfs[markedConfIdx] )
                            confChanged = False
                        elif mod & pygame.KMOD_LCTRL:
                            if len(self.markedConfs) > 1 and not confChanged:
                                self.markedConfs.pop(markedConfIdx)
                                self.display.setText( "Kill conf " 
                                                     + str(markedConfIdx) )
                                markedConfIdx=(markedConfIdx-1)%len(self.markedConfs)
                        else:
                            markedConfIdx=(markedConfIdx+1)%len(self.markedConfs)
                            self.display.setText( "Load marked conf " 
                                                  + str(markedConfIdx) )
                            self.ca.setConf( self.markedConfs[markedConfIdx] )
                            confChanged = False
                        if self.ca.getSize() != self.display.getSize():
#                            print "not same size:", self.ca.getSize(), self.display.getSize()
                            self.display.__init__( self.ca.getSize(), 
                                                   self.display.scale, 
                                                   self.ca.palette, 
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

def sim():
    simulator = Simulator()
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

    
### starting new process for sim ###

#this Queue should be known to all subsequent processes...
globalEventQueue = Queue()

simProc = Process( target=sim, args=() )
simProc.start()

