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
from CA import sandPile, catPile, binRule, ballPile, ballRule, vonNeumann
import Histogram
import sys 
import time
from os import path, getcwd, chdir, listdir, path, system
import optparse
import Display


class Simulator():
    def __init__( self, CAType, confFile, random, sizeX, sizeY, scale, oneLiner ):
        self.oneLiner = oneLiner
        if CAType.upper() == "SANDPILE":
            if random:
                self.ca = sandPile( sizeX, sizeY, sandPile.INIT_RAND )
            else:
                self.ca = sandPile( sizeX, sizeY, sandPile.INIT_ZERO )
            self.display = Display.DisplaySquares2D( self.ca.getSize(), float(scale),
                                                     self.ca.palette, self.ca.getDim() )
        elif CAType[0:7].upper() == "BINRULE":
            if random:
                self.ca = binRule( int(CAType[7:]), sizeX, sizeY, binRule.INIT_RAND )
            else:
                self.ca = binRule( int(CAType[7:]), sizeX, sizeY, binRule.INIT_ZERO )
            self.display = Display.DisplaySquares1D( self.ca.getSize(), float(scale),
                                                   self.ca.palette, self.ca.getDim(),
                                                   self.oneLiner )
        elif CAType[0:8].upper() == "BALLRULE":
            if random:
                self.ca = ballRule( int(CAType[8:]), sizeX, sizeY, ballRule.INIT_RAND )
            else:
                self.ca = ballRule( int(CAType[8:]), sizeX, sizeY, ballRule.INIT_ZERO )
            self.display = Display.DisplayImages1D( self.ca.getSize(), float(scale),
                                                    self.ca.palette, self.ca.getDim(),
                                                    self.oneLiner )
            
        elif CAType.upper() == "BALLPILE":
            if random:
                self.ca = ballPile( sizeX, sizeY, ballPile.INIT_RAND )
            else:
                self.ca = ballPile( sizeX, sizeY, ballPile.INIT_ZERO )
            self.display = Display.DisplayImages2D( self.ca.getSize(), float(scale),
                                                    self.ca.palette, self.ca.getDim() )

        elif CAType.upper() == "VONNEUMANN":
            self.ca = vonNeumann( sizeX, sizeY )
            self.display = Display.DisplayImages2D( self.ca.getSize(), float(scale),
                                                    self.ca.palette, self.ca.getDim() )

        if confFile != "":
            self.ca.importConf( confFile )

        self.histograms = []
#        self.histograms.append( Histogram.VBars( 8, 1600, self.ca.palette, self.ca.info ) )


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
                            msg="Set name for marked conf", default="" )
                        self.markedConfNames.append( confName )
                        self.display.drawConf( self.ca.getConf(), True )
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
                                msg="Open conf from file", default=filename, fileHandling=True )
                            while not path.exists( filename ) and filename != "":
                                self.display.setText( "File does not exist" )
                                time.sleep( 1 )
                                filename = self.display.getUserInputKey( 
                                    msg="Open conf from file", default=filename, fileHandling=True )
                                if filename == "":
                                    break
                            if ( filename != "" and
                                 filename != "Conf_<Title>_<SizeX>x<SizeY>_<Number>.cnf" ):
                                    
                                ret = self.ca.importConf( filename )
                                if ret == self.ca.IMPORTOK:
                                    self.display.setText( "Opened file" + filename )
                                elif ret == self.ca.SIZECHANGED:
#                                    print self.ca.getSize()
                                    self.display.__init__( self.ca.getSize(), self.display.scale, 
                                                           self.ca.palette, self.display.dim )
                                elif ret == self.ca.WRONGCA:
                                    print "WRONGCA"
                                    sys.exit(1)
                                    pass
                                elif ret == self.ca.IMPORTNOTOK:
                                    print "IMPORTNOTOK"
                                    sys.exit(1)
                                    pass
                            else:
                                self.display.drawConf( self.ca.getConf(), True )
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
                                msg="Save conf to file", default=filename, fileHandling=True )
                            flag = True
                            if filename == "":
                                self.display.setText( "Cancelled" )
                                flag = False
                            flag &= path.exists( filename )
                            while ( flag ):
                                self.display.setText( "File exists! Overwrite? [n/y]" )
                                for e in pygame.event.get():
                                    if e.type == pygame.KEYDOWN:
                                        if e.unicode == "y":
                                            flag = False
                                        elif e.unicode == "n":
                                            filename = self.display.getUserInputKey( 
                                                msg="Save conf to file", default=filename )
                                            if filename == "":
                                                flag = False
                                            flag &= path.exists( filename )
                            
                            if filename == "":
                                self.display.drawConf( self.ca.getConf(), True )
                                self.display.setText( "Cancelled" )
                            else:
                                self.ca.exportConf( filename )
                                self.display.drawConf( self.ca.getConf(), True )
                                self.display.setText( "Saved to " + filename )

                        else:
                            self.ca.step()
                            stepCounter += 1
                            self.display.drawConf( self.ca.getConf(), not self.oneLiner )
                            self.display.setText( "Step" )

                    elif e.key == pygame.K_RIGHT or e.key == pygame.K_LEFT \
                            or e.key == pygame.K_UP or e.key == pygame.K_DOWN:
                        self.display.scroll( e.key )

                    elif e.key == pygame.K_SPACE:
                        loop = not(loop)
                        msg = "Stop"
                        if loop: 
                            msg = "Start"
                        if self.display.textAlive:
                            self.display.drawConf( self.ca.getConf(), self.oneLiner )
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

            self.display.drawConf( self.ca.getConf(), not self.oneLiner and loop )
            self.display.showText()
            if showStepCount:
                self.display.showCounter( stepCounter )
            self.display.update()

    def step( self, n ):
        self.ca.loopFunc()
        self.display.update()

    def stop( self ):
        pass

def sim( CAType, confFile, random, sizeX, sizeY, scale, oneLiner ):
    simulator = Simulator( CAType, confFile, random, sizeX, sizeY, scale, oneLiner )
    simulator.start()


### user interface functions ###
def start():
    print "starting simulation"
    globalEventQueue.put( "start" )

def step():
    print "doing one step"
    globalEventQueue.put( "step" )

def stop():
    print "stopping simulation"
    globalEventQueue.put( "stop" )

def quit():
    print "sending quit-message to everyone"
    globalEventQueue.put( "quit" )
    simProc.join()
    print "exiting..."
    sys.exit(0)


def listCA():
    print "Available CA: SandPile, BallPile, Binrule, Ballrule, vonNeumann"
    sys.exit(0)

if __name__ == "__main__":
    if "-i" in sys.argv:
        cmd = "python -i"
        for a in sys.argv:
            if a != "-i":
                cmd = cmd + " " + a
        system( cmd )

    parser = optparse.OptionParser(version = "CASimulator 0.1")
    parser.add_option( "-f", "--file", default="", dest="confFile", 
                       help="Load initial configuration from FILE" )
    parser.add_option( "-i", "--interactive", action="store_true", dest="interactive", help="start sim.py interactively" )
    parser.add_option( "-l", "--list", action="store_true", default=False, dest="listCA", 
                       help="List types of supported CA" )
    parser.add_option( "-n", "--binRuleNr", default=110, dest="binRuleNr",
                       help="Define number of binary rule [110]", type=int )
    parser.add_option( "-r", "--random", action="store_true", default=False, dest="random", 
                       help="Set initial configuration to RANDOM [False]" )
    parser.add_option( "-s", "--scale", default=20.0, dest="scale", 
                       help="Set the measure by which a state's display is scaled [20.0]", type=float ) 
    parser.add_option( "-t", "--type",  default="SandPile", dest="CAType", 
                       help="Set type of CA (e.g. 'SandPile' or 'Binrule') [SandPile]" )
    parser.add_option( "-x", "--sizeX", default=20, dest="sizeX", help="width of CA [20]", type=int )
    parser.add_option( "-y", "--sizeY", default=20, dest="sizeY", help="height of CA [20]", type=int )  
    parser.add_option( "-1", "--oneLiner", action="store_true", default=False, dest="oneLiner", 
                       help="Show only the current configuration (only useful for 1dimensional CA) [False]" )
    (options, args) = parser.parse_args()

    
    if options.listCA:
        listCA()
        sys.exit(1)

    if options.CAType.upper() not in ("SANDPILE", "BINRULE", "BALLPILE", "BALLRULE", "VONNEUMANN" ):
        print "You didn't specify a correct type of cellular automaton."
        print "You can get all supported types by passing the argument -l"
        sys.exit(1)

    if options.CAType.upper() in ( "BINRULE", "BALLRULE" ):
        if options.oneLiner == True:
            # if only one line is displayed, space for displayed text messages is needed
            options.sizeY = 2
        if not( 0 <= options.binRuleNr < 256):
            print "The binrule number has to be in [0,255]"
            sys.exit(0)
        else:
            if options.random == False:
                print "Initialized to all-zero! Try option '-r' for randomized initialization"
            modCAType = options.CAType.upper()+str(options.binRuleNr)
    else:
        modCAType = options.CAType

    if options.confFile != "" and not path.exists(options.confFile):
        print "The given confFile you named does not exists! Exiting..."
        sys.exit(1)

    # this Queue should be known to all subsequent processes...
    globalEventQueue = Queue()
    simProc = Process( target=sim, args=( modCAType,
                                          options.confFile,
                                          options.random,
                                          options.sizeX,
                                          options.sizeY,
                                          options.scale,
                                          options.oneLiner) )
    simProc.start()
