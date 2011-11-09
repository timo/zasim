

## The cellular automaton proposed by John von Neumann
# \verbatim
# All states are encoded in a bitmask:
#
#    <--MSB                     10                              LSB
#  ...... 0 0 0 0 0 0 0 0 0 X X u a1 a0 eps sc1 sc0 s2 s1 s0 e1 e0
#                           | | | |  |  |    |   |   |  |  |  |  |-> current e
#  XX = 00 -> U    <--------| | | |  |  |    |   |   |  |  |  |----> next e
#  XX = 01 -> C    <----------| | |  |  |    |   |   |  |  |
#  XX = 10 -> S                 | |  |  |    |   |   |  |  |-------> lsb on S
#  XX = 11 -> T                 | |  |  |    |   |   |  |----------> ...
#                               | |  |  |    |   |   |-------------> msb on S
#  S{} is encoded as SMASK_111  | |  |  |    |   |-----------------> s-state counter
#                               | |  |  |    |---------------------> s-state counter
#                               | |  |  |
#                               | |  |  |--------------------------> excited
#                               | |  |-----------------------------> direction
#                               | |--------------------------------> direction
#                               |----------------------------------> special
#
# \endverbatim
class vonNeumann ( CA ):
    palette = []
    ## The constructor
    def __init__( self, sizeX, sizeY, confFile ):
        ## The ca's title
        self.title = "vonNeumann"
        ## The ca's dimension
        self.dim = 2
        self.size = self.sizeX, self.sizeY = sizeX, sizeY

        ## A map from states according to the bitmask to
        # pygame blittable states ( between 0 and 28 )
        self.displayableStateDict = {
            0: 0,     # U
            2048: 1,  #C00   2048
            2049: 2,  #C10   2048+1
            2050: 3,  #C01   2048+2
            2051: 4,  #C11   2048+3
            4192: 5,  #S000  4096+96
            4160: 6,  #S00   4096+64
            4168: 7,  #S01   4096+64+8
            4128: 8,  #S0    4096+32
            4176: 9,  #S10   4096+64+16
            4184: 10, #S11   4096+64+16+8
            4144: 11, #S1    4096+32+16
            4096: 12, #S     4096
            6144: 13, #T000  6144
            6272: 14, #T001  6144+128
            6400: 15, #T010  6144+256
            6528: 16, #T011  6144+128+256
            6656: 17, #T020  6144+512
            6784: 18, #T021  6144+128+512
            6912: 19, #T030  6144+256+512
            7040: 20, #T031  6144+128+256+512
            7168: 21, #T100  6144+1024
            7296: 22, #T101  6144+128+1024
            7424: 23, #T110  6144+256+1024
            7552: 24, #T111  6144+128+256+1024
            7680: 25, #T120  6144+512+1024
            7808: 26, #T121  6144+128+512+1024
            7936: 27, #T130  6144+256+512+1024
            8064: 28, #T131  6144+128+256+1024+512
            }

        ## A map from human readable vonNeumann states ( such as 'U', 'T020' and 'C11' )
        # actual states calculated via bitmask
        self.nameStateDict = { "U": 0,
                               "C00" : 2048, "C10" : 2049, "C01" : 2050, "C11" : 2051,
                               "S"   : 4096, "S0"  : 4128, "S1"  : 4144, "S00" : 4160,
                               "S01" : 4168, "S10" : 4176, "S11" : 4184, "S000": 4192,
                               "T000": 6144, "T001": 6272, "T010": 6400, "T011": 6528,
                               "T020": 6656, "T032": 6784, "T030": 6912, "T031": 7040,
                               "T100": 7168, "T101": 7296, "T110": 7424, "T111": 7552,
                               "T120": 7680, "T121": 7808, "T130": 7936, "T131": 8064 }

        ## An array containing all correct states (see vonNeumann)
        self.states = [ 0, 2048, 2049, 2050, 2051, 4096, 4128, 4144, 4160, 4168,
                        4176, 4184, 4192, 6144, 6272, 6400, 6528, 6656, 6784,
                        6912, 7040, 7168, 7296, 7424, 7552, 7680, 7808, 7936, 8064 ]

        ## The current configuration is held here
        # as usual, these two arrays contain the real configuration, that is used
        # in every step ... (see vonNeumann::displayConf)
        self.currConf = np.zeros( (sizeX, sizeY), int )
        ## The current configuration is held here
        self.nextConf = np.zeros( (sizeX, sizeY), int )
        # used when updating only some cells instead of all....
        self.cActArr = np.zeros( (self.sizeX*self.sizeY), bool )
        self.nActArr = np.zeros( (self.sizeX*self.sizeY), bool )
        self.cList = np.zeros( (self.sizeX*self.sizeY), int )
        self.nList = np.zeros( (self.sizeX*self.sizeY), int )
        self.cCounter = 0
        self.nCounter = 0
        if confFile != "":
            self.importConf( confFile )
            self.nextConf = self.currConf.copy()
        ## The configuration that is blittet...
        # But in this CA the states are not enumerable from 0..28, but scattered
        # between 0 and ~2^13, so we need a dict (see vonNeumann::displayableStateDict)
        # to map the states to 0..28, so the Display-module can display states
        # without knowing the difference
        self.displayConf = np.zeros( self.size, int)


        for imgFile in ( "images/vonNeumann/U.jpg",    "images/vonNeumann/C00.jpg",
                         "images/vonNeumann/C01.jpg",  "images/vonNeumann/C10.jpg",
                         "images/vonNeumann/C11.jpg",  "images/vonNeumann/S000.jpg",
                         "images/vonNeumann/S00.jpg",  "images/vonNeumann/S01.jpg",
                         "images/vonNeumann/S0.jpg",   "images/vonNeumann/S10.jpg",
                         "images/vonNeumann/S11.jpg",  "images/vonNeumann/S1.jpg",
                         "images/vonNeumann/S.jpg",    "images/vonNeumann/T000.jpg",
                         "images/vonNeumann/T001.jpg", "images/vonNeumann/T010.jpg",
                         "images/vonNeumann/T011.jpg", "images/vonNeumann/T020.jpg",
                         "images/vonNeumann/T021.jpg", "images/vonNeumann/T030.jpg",
                         "images/vonNeumann/T031.jpg", "images/vonNeumann/T100.jpg",
                         "images/vonNeumann/T101.jpg", "images/vonNeumann/T110.jpg",
                         "images/vonNeumann/T111.jpg", "images/vonNeumann/T120.jpg",
                         "images/vonNeumann/T121.jpg", "images/vonNeumann/T130.jpg",
                         "images/vonNeumann/T131.jpg" ):
            img = None #pygame.image.load( imgFile ).convert()
            self.palette.append( img )


    ## Used to append cells to the list of cells to handle in the next step
    def enlist( self, x, y ):
        for i in ( ( (x)   + (y)*self.sizeX ),
                   ( (x+1) + (y)*self.sizeX ),
                   ( (x-1) + (y)*self.sizeX ),
                   ( (x) + (y-1)*self.sizeX ),
                   ( (x) + (y+1)*self.sizeX ) ):
            if self.cActArr[ i ] == False:
                self.cActArr[ i ] = True
                self.cList[self.cCounter] = i
                self.cCounter += 1

    def click_on_cell( self, x, y, mousekey, mods ):
        EPS = 128
        SPECIAL = 1024
        CSTATE = 2048
        SSTATE = 4096
        TSTATE = 6144

        if x <= 0 or x >= self.sizeX-1 or y <= 0 or y >= self.sizeY-1:
            return
        state = self.states[self.displayConf[x][y]]
        s = 0

        if e.button == 1:
            # T-states
            s = TSTATE
            if mods & pygame.KMOD_LCTRL:
                # eps
                if state & EPS == 0 and (state & TSTATE == TSTATE):
                    # to just insert a new eps without changing anything
                    self.currConf[x][y] = state+EPS
                    self.nextConf[x][y] = state+EPS
                    self.enlist(x,y)
                    return
                s += EPS
            if mods & pygame.KMOD_LSHIFT:
                # u
                s += SPECIAL
            if state == 0:
                for nbs in ( self.states[self.displayConf[x+1][y]],
                             self.states[self.displayConf[x][y-1]],
                             self.states[self.displayConf[x-1][y]],
                             self.states[self.displayConf[x][y+1]] ):
                    if ( nbs & TSTATE == TSTATE ) \
                            and ( ( mods & pygame.KMOD_LSHIFT == state & SPECIAL ) \
                                      and ( mods & pygame.KMOD_LCTRL == state & EPS ) ):
                        s += nbs & 768
                        self.currConf[x][y] = s
                        self.nextConf[x][y] = s
                        self.enlist(x,y)
                        return
            s += (((state&768)+256) & 768)
            self.currConf[x][y] = s
            self.nextConf[x][y] = s
            self.enlist(x,y)
        if e.button == 3:
            if mods & pygame.KMOD_LCTRL:
                # C-states
                s = CSTATE
                s += (((state&3)+1) & 3)
            elif mods & pygame.KMOD_LSHIFT:
                # S-states
                if state == 0 or (state & SSTATE) != SSTATE:
                    s = SSTATE
                    self.currConf[x][y] = s
                    self.nextConf[x][y] = s
                    self.enlist(x,y)
                    return
                sIdx = ( ( self.displayableStateDict[state] - 5 + 1 ) % 8 ) + 5
                s = self.states[sIdx]
            else:
                # U-state
                s = 0
            self.currConf[x][y] = s
            self.nextConf[x][y] = s
            self.enlist(x,y)

    def getConf( self ):
        for i in range( 1, self.sizeX-1 ):
            for j in range( 1, self.sizeY-1 ):
                if self.displayableStateDict.has_key( self.currConf[i][j] ):
                    self.displayConf[i][j] = self.displayableStateDict[self.currConf[i][j]]
                else:
                    print "Unkown state in cell", i, j, ":", self.currConf[i][j]
        return self.displayConf

    def importConf( self, filename ):
        with open( filename, 'r' ) as f:
            line = f.readline()
            while line[0:1] == "#":
                line = f.readline()
            if line[0:4] != "x = ":
                # fall back to familiar CASimulator/Xasim fileformat
                CA.importConf( self, filename )
            else:

                line = line[4:]
                sizeX = 0
                sizeX = int(line[0:line.find(",")])+2
                line = line[line.find("y = ")+4:]
                sizeY = 0
                sizeY = int(line[0:line.find(",")])+2
                line = line[line.find("rule = ")+7:]
                rule = line[:-1]

                if sizeX != self.sizeX or sizeY != self.sizeY:
                    self.resize( sizeX, sizeY )

                rleStateDict = { ".": "U",
                                 "A": "S",     "B": "S0",    "C": "S1",    "D": "S00",
                                 "E": "S01",   "F": "S10",   "G": "S11",   "H": "S000",
                                 "I": "T000",  "J": "T010",  "K": "T020",  "L": "T030",
                                 "M": "T001",  "N": "T011",  "O": "T021",  "P": "T031",
                                 "Q": "T100",  "R": "T110",  "S": "T120",  "T": "T130",
                                 "U": "T101",  "V": "T111",  "W": "T121",  "X": "T131",
                                 "pA": "C00",  "pB": "C01",  "pC": "C10",  "pD": "C11" }

# 63.8ILILILILIL$63.J.J.pA.pA.IJIJIJIJL$63.J.J.J.J9.IL$57.IL4IpAIpAIpAI
# pAIpAIpAIpAIpA.LK$57.JIJ3.L.L.2LKLKLKLKLK.IL$57.J5.L.L.LILILILILIL.LK
# .IL$57.J5.L.L.L.L.L.L.pA.pA.L2.JL$57.J5.16IL2.JL$57.J15.L6K2.JL$52.IL
# IL.J5.10ILILILILILJL$52.JLJL.J5.J.J.pA.pA.pA.IJIJLJLJLJL$52.JLJL.J.IL
# 2.J.J.J.J.J5.IJIJIJL$52.JLJL.J.J3IpAIpAIpAIpAIpAIpAIpA.L6K$52.JLJL.J.
# J3.L.L.L.L.L.2LK.IL$52.JLJL.J.J3.L.L.L.L.L.LIL.JL$52.JLJL.J.J3.L.L.L.
# L.L.2LK.JL$52.JLJL.J.J3.L.L.L.L.L.LIL.JLIL$52.JLJL.J.J3.L.L.L.pA.pA.p
# .L.JLJL$52.JLJL.J.J3.14IJIJ5IL$52.JLJLIpAIpA25IL$52.JIJI2J.J25.L$52.J


                # since RLE-configuration files don't imply ghostcells, they are added here!
                x = 1
                y = 1
                mx = 0
                importRegexp = re.compile( "((\d*)(\.|(p*)[A-X]))|(\$)|(\!)" )
                for line in f:
                    content = importRegexp.findall( line[0:-2] )
                    for c in content:
                        if c[0] != "":
                            if c[1] != "":
                                r = int(c[1])
                            else:
                                r = 1
                            for s in range(r):
                                self.currConf[x][y] = self.nameStateDict[rleStateDict[c[2]]]
                                x += 1
                        elif c[4] != "":
                            if x > mx:
                                mx = x
                            x = 1
                            y += 1
                        elif c[5] != "":
                            break

                self.nextConf = self.currConf.copy()
                f.close()

        # now, get all active cells:
        for x in range(1,self.sizeX-1):
            for y in range(1,self.sizeY-1):
                if self.currConf[x,y] in ( 2049, 2050, 2051, 4096, 4128, 4144, 4160,
                                           4168, 4176, 4184, 4192, 6272, 6528, 6784,
                                           7040, 7296, 7552, 7808, 8064 ):
                    self.enlist(x,y)


    def loopFunc( self ):
        self.step()

    def resize( self, sizeX, sizeY = None ):
        CA.resize( self, sizeX, sizeY )
        self.displayConf = np.zeros( self.size, int )
        self.cActArr = np.zeros( self.sizeX*self.sizeY, bool )
        self.nActArr = np.zeros( self.sizeX*self.sizeY, bool )
        self.cList = np.zeros( (self.sizeX*self.sizeY), int )
        self.nList = np.zeros( (self.sizeX*self.sizeY), int )

    def setConf( self, conf ):
        if conf.shape != self.currConf.shape:
            self.resize( conf[0].size, conf[1].size )
        for i in range( 1, self.sizeX-1 ):
            for j in range( 1, self.sizeY-1 ):
                self.currConf[i][j] = self.states[conf[i][j]]
                self.nextConf[i][j] = self.states[conf[i][j]]

    ## Calls the actual function that is used to calculate the next configuration
    def step( self ):
        self.updateAllCellsWeaveInlineFewStates()
#        self.updateAllCellsWeaveInline()

    ## Updates all cells using scipy.weave.inline
    def updateAllCellsWeaveInline( self ):
#
# All states are encoded in a bitmask:
#
#    <--MSB                     10                              LSB
#  ...... 0 0 0 0 0 0 0 0 0 X X u a1 a0 eps sc1 sc0 s2 s1 s0 e1 e0
#                           | | | |  |  |    |   |   |  |  |  |  |-> current e
#  XX = 00 -> U    <--------| | | |  |  |    |   |   |  |  |  |----> next e
#  XX = 01 -> C    <----------| | |  |  |    |   |   |  |  |
#  XX = 10 -> S                 | |  |  |    |   |   |  |  |-------> lsb on S
#  XX = 11 -> T                 | |  |  |    |   |   |  |----------> ...
#                               | |  |  |    |   |   |-------------> msb on S
#  S{} is encoded as SMASK_111  | |  |  |    |   |-----------------> s-state counter
#                               | |  |  |    |---------------------> s-state counter
#                               | |  |  |
#                               | |  |  |--------------------------> excited
#                               | |  |-----------------------------> direction
#                               | |--------------------------------> direction
#                               |----------------------------------> special
#
        vonNeumannCode = """
#include <stdlib.h>
#include <stdio.h>

#line 1 "CA.py"
#define UMASK          0
#define CMASK       2048  // 1 << 11
#define SMASK       4096  // 2 << 11
#define TMASK       6144  // 3 << 11
#define CSTATEMASK     3  // 1|2
#define SSTATEMASK    28  // 4|8|16
#define TSTATEMASK  1920  // 128|256|512|1024
#define e0     1
#define e1     2
#define s0     4
#define s1     8
#define s2    16
#define s     28  // s2|s1|s0
#define sc0   32
#define sc1   64
#define sc    96  // sc1|sc0
#define eps  128
#define a0   256
#define a1   512
#define a    768  // a1|a0
#define u   1024

#define U(x) ((x) == 0)
#define C(x) (((x) & CMASK) == CMASK)
#define S(x) (((x) & SMASK) == SMASK)
#define T(x) (((x) & TMASK) == TMASK)

#define A_UNSHIFT(x)  (((x)&a)>>8)
#define SC_SHIFT(x)   ((x)<<5)
#define SC_UNSHIFT(x) (((x)&sc)>>5)

  int i, j, k, l;
  int nbs[4];
  int state;
  for ( i = 1; i < sizeX-1; i++ ) {
    for ( j = 1; j < sizeY-1; j++ ) {
      state = cconf( i, j );
      nbs[0] = cconf( i+1, j );
      nbs[1] = cconf( i, j-1 );
      nbs[2] = cconf( i-1, j );
      nbs[3] = cconf( i, j+1 );

      if ( T(state) ) { // transmission state
        // transisition rule (T.1):
        for ( k = 0; k < 4; k++ ) {
          if ( T(nbs[k]) && ( abs(k-(A_UNSHIFT(nbs[k]))) == 2)
               && ((nbs[k]&u) != (state&u)) && (nbs[k]&eps)  ) {
            // (T.1)(alpha)
            nconf( i, j ) = UMASK;
            break;
          }
        }
        if ( k < 4 ) continue;

        // (T.1)(beta)
        for ( k = 0; k < 4; k++ ) {
          if ( T(nbs[k]) && (abs((A_UNSHIFT(nbs[k]))-(A_UNSHIFT(state))) != 2)
               && (abs(k-(A_UNSHIFT(nbs[k]))) == 2)
               && ((nbs[k]&u) == (state&u) ) && (nbs[k]&eps) ) {
            // (T.1)(beta)(a)
            nconf( i, j ) = state | eps;
            break;
          }
          if ( C(nbs[k]) && (nbs[k]&e0) && (k-(A_UNSHIFT(state)) != 0) ) {
            // (T.1)(beta)(b)
            nconf( i, j ) = state | eps;
            break;
          }
        }

        if ( k < 4 ) continue;

        // (T.1)(gamma)
        nconf( i, j ) = TMASK | (state&u) | (state&a);
      } // end of T(state)


      else if ( C(state) ) { // confluent state
        // transistion rule (T.2)
        for ( k = 0; k < 4; k++ ) {
          if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2)
               && (nbs[k]&eps) && (nbs[k]&u) ) {
            // (T.2)(alpha)
            nconf( i, j ) = UMASK;
            break;
          }
        }
        if ( k < 4 ) continue;

        // (T.2)(beta)
        for( k = 0; k < 4; k++ ) {
          if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2)
               && (nbs[k]&eps) && !(nbs[k]&u) ) {
            // (T.2)(beta)(a)
            break;
          }
        }
        if ( k < 4 ) {
          for ( k = 0; k < 4; k++ ) {
            if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2)
                 && !(nbs[k]&eps) && !(nbs[k]&u) ) {
              // (T.2)(beta)(b)
              break;
            }
          }
          if ( k == 4 ) {
            nconf( i, j ) = CMASK | e1 | ((state&e1)>>1);
            continue;
          }
        }

        // (T.2)(gamma)
        nconf( i, j ) = CMASK | ((state&e1)>>1);
      } // end of C(state)

      else if ( U(state) ) {  // unexcitable state
        // transition rule (T.3)
        for ( k = 0; k < 4; k++ ) {
          if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
            // (T.3)(alpha)
            nconf( i, j ) = SMASK;
            break;
          }
        }
        // (T.3)(beta)
        // doesn' change the state
      } // end of U(state)

      else if ( S(state) ) { // sensitized state
        if ( !(state&sc1)  ) {
          // transition rule (T.4)
          for ( k = 0; k < 4; k++ ) {
            if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
              // (T.4)(alpha)
              nconf( i, j ) = state | (s0<<(2-SC_UNSHIFT(state)));
              break;
            }
          }
          // (T.4)(beta)
          // doesn't change the state but the counter
          nconf( i, j ) += sc0;
        } else {
          if ( (state&sc) == sc ) {
            for ( k = 0; k < 4; k++ ) {
              if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
                nconf( i, j ) = TMASK | a0;
                break;
              }
            }
            if ( k == 4 ) {
              nconf( i, j ) = TMASK;
            }
          } else {
            for ( k = 0; k < 4; k++ ) {
              if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
                nconf( i, j ) = state | s0;
                break;
              }
            }
            nconf( i, j ) += sc0;

            if ( nconf( i, j ) & s ) {
              // make transition from sensitized to transmission or confluent state
              l = nconf( i, j );
              if ( (l & s) == s ) {
                nconf( i, j ) = CMASK;
              } else {
                // other leaves of the S-to-T-transition tree of depth 3
                l += s0;
                nconf( i, j ) = TMASK | ((l&s)<<6);
              }
            }
          }// else {
            // stay for another run
        //}
        }
      }

      else  {
    // this state is undefined!
      }
    }
  }
"""

        cconf = self.currConf
        nconf = self.nextConf
        sizeX = self.sizeX
        sizeY = self.sizeY
        weave.inline( vonNeumannCode, [ 'cconf', 'nconf', 'sizeX', 'sizeY' ],
                      type_converters = converters.blitz,
                      compiler = 'gcc' )
        self.currConf = self.nextConf.copy()


    ## Update cells, but only those that changed or are in the neighbourhood of one of those.
    # This is done via bitchecking, and hence admittedly difficult to read.
    # Every subsection of the transitionfunction from von Neumann's paper is marked.
    def updateAllCellsWeaveInlineFewStates( self ):
#
# All states are encoded in a bitmask:
#
#    <--MSB                     10                              LSB
#  ...... 0 0 0 0 0 0 0 0 0 X X u a1 a0 eps sc1 sc0 s2 s1 s0 e1 e0
#                           | | | |  |  |    |   |   |  |  |  |  |-> current e
#  XX = 00 -> U    <--------| | | |  |  |    |   |   |  |  |  |----> next e
#  XX = 01 -> C    <----------| | |  |  |    |   |   |  |  |
#  XX = 10 -> S                 | |  |  |    |   |   |  |  |-------> lsb on S
#  XX = 11 -> T                 | |  |  |    |   |   |  |----------> ...
#                               | |  |  |    |   |   |-------------> msb on S
#  S{} is encoded as SMASK_111  | |  |  |    |   |-----------------> s-state counter
#                               | |  |  |    |---------------------> s-state counter
#                               | |  |  |
#                               | |  |  |--------------------------> excited
#                               | |  |-----------------------------> direction
#                               | |--------------------------------> direction
#                               |----------------------------------> special
#
#
        vonNeumannCodeFewStates = """
#include <stdlib.h>
#include <stdio.h>

#line 1 "VonNeumannDefinesInCA.py"
#define UMASK          0
#define CMASK       2048  // 1 << 11
#define SMASK       4096  // 2 << 11
#define TMASK       6144  // 3 << 11
#define CSTATEMASK     3  // 1|2
#define SSTATEMASK    28  // 4|8|16
#define TSTATEMASK  1920  // 128|256|512|1024
#define e0     1
#define e1     2
#define s0     4
#define s1     8
#define s2    16
#define s     28  // s2|s1|s0
#define sc0   32
#define sc1   64
#define sc    96  // sc1|sc0
#define eps  128
#define a0   256
#define a1   512
#define a    768  // a1|a0
#define u   1024

/* checkers for different kinds of states */
#define U(x) ((x) == 0)
#define C(x) (((x) & CMASK) == CMASK)
#define S(x) (((x) & SMASK) == SMASK)
#define T(x) (((x) & TMASK) == TMASK)

/* get the direction of a T-state and the 'age' of an S-state */
#define A_UNSHIFT(x)  (((x)&a)>>8)
#define SC_SHIFT(x)   ((x)<<5)
#define SC_UNSHIFT(x) (((x)&sc)>>5)

/* enlist a cell to be checked in the next step */
#define ENLIST(id) if ( !nActArr( (id) ) ) {\
                     nActArr( id ) = true;\
                     nList( nCounter++ ) = id;\
                   }

/* enlist a cell and it's neighbourhood to be checke in the next step */
#define MARKNBH(x,y) ENLIST( (x)+(y)*sizeX );\
                     ENLIST( (x+1)+(y)*sizeX );\
                     ENLIST( (x-1)+(y)*sizeX );\
                     ENLIST( (x)+(y-1)*sizeX );\
                     ENLIST( (x)+(y+1)*sizeX );


#include <stdio.h>
#line 1 "VonNeumannCodeInCA.py"
int i, j, k, l, x, y, aa;

/* the neighbours' states */
int nbs[4];
/* the 'own' state */
int state;
/* the number of cells that have to be checked in the next step and is returned as return_val */
int nCounter = 0;
for ( i = 0; i < cCounter; i++ ) {
  x = cList( i ) % sizeX;
  y = cList( i ) / sizeX;
  cActArr( cList( i ) ) = false;

  state = cconf( x, y );
  nbs[0] = cconf( x+1, y );
  nbs[1] = cconf( x, y-1 );
  nbs[2] = cconf( x-1, y );
  nbs[3] = cconf( x, y+1 );

  if ( T(state) ) { // transmission state
    // transisition rule (T.1):
    for ( k = 0; k < 4; k++ ) {
      if ( T(nbs[k]) && ( abs(k-(A_UNSHIFT(nbs[k]))) == 2)
           && ((nbs[k]&u) != (state&u)) && (nbs[k]&eps)  ) {
        // (T.1)(alpha)
        nconf( x, y ) = UMASK;
        break;
      }
    }
    if ( k < 4 ) continue;

    // (T.1)(beta)
    for ( k = 0; k < 4; k++ ) {
      if ( T(nbs[k]) && (abs((A_UNSHIFT(nbs[k]))-(A_UNSHIFT(state))) != 2)
           && (abs(k-(A_UNSHIFT(nbs[k]))) == 2)
           && ((nbs[k]&u) == (state&u) ) && (nbs[k]&eps) ) {
        // (T.1)(beta)(a)
        nconf( x, y ) = state | eps;
        MARKNBH( x, y );
        break;
      }
      if ( C(nbs[k]) && (nbs[k]&e0) && (k-(A_UNSHIFT(state)) != 0) ) {
        // (T.1)(beta)(b)
        nconf( x, y ) = state | eps;
        MARKNBH( x, y );
        break;
      }
    }

    if ( k < 4 ) continue;

    // (T.1)(gamma)
    // don't enlist, since cell is not active
    // MARKNBH( x, y );
    nconf( x, y ) = TMASK | (state&u) | (state&a);
  } // end of T(state)


  else if ( C(state) ) { // confluent state
    // transistion rule (T.2)
    for ( k = 0; k < 4; k++ ) {
      if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2)
           && (nbs[k]&eps) && (nbs[k]&u) ) {
        // (T.2)(alpha)
        // don't enlist, since cell is not active
        nconf( x, y ) = UMASK;
        break;
      }
    }
    if ( k < 4 ) continue;

    // (T.2)(beta)
    for( k = 0; k < 4; k++ ) {
      if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2)
           && (nbs[k]&eps) && !(nbs[k]&u) ) {
        // (T.2)(beta)(a)
        MARKNBH( x, y );
        break;
      }
    }
    if ( k < 4 ) {
      for ( k = 0; k < 4; k++ ) {
        if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2)
             && !(nbs[k]&eps) && !(nbs[k]&u) ) {
          // (T.2)(beta)(b)
          MARKNBH( x, y );
          break;
        }
      }
      if ( k == 4 ) {
        nconf( x, y ) = CMASK | e1 | ((state&e1)>>1);
        MARKNBH( x, y );
        continue;
      }
    }

    // (T.2)(gamma)
    nconf( x, y ) = CMASK | ((state&e1)>>1);
    MARKNBH( x, y );
  } // end of C(state)

  else if ( U(state) ) {  // unexcitable state
    // transition rule (T.3)
    for ( k = 0; k < 4; k++ ) {
      if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
        // (T.3)(alpha)
        nconf( x, y ) = SMASK;
        MARKNBH( x, y );
        break;
      }
    }
    // (T.3)(beta)
    // doesn' change the state
  } // end of U(state)

  else if ( S(state) ) { // sensitized state
    MARKNBH( x, y );
    if ( !(state&sc1)  ) {
      // transition rule (T.4)
      for ( k = 0; k < 4; k++ ) {
        if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
          // (T.4)(alpha)
          nconf( x, y ) = state | (s0<<(2-SC_UNSHIFT(state)));
          break;
        }
      }
      // (T.4)(beta)
      // doesn't change the state but the counter
      nconf( x, y ) += sc0;
    } else {
      if ( (state&sc) == sc ) {
        for ( k = 0; k < 4; k++ ) {
          if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
            nconf( x, y ) = TMASK | a0;
            break;
          }
        }
        if ( k == 4 ) {
          nconf( x, y ) = TMASK;
        }
      } else {
        for ( k = 0; k < 4; k++ ) {
          if ( T(nbs[k]) && (abs(k-A_UNSHIFT(nbs[k])) == 2) && (nbs[k]&eps) ) {
            nconf( x, y ) = state | s0;
            break;
          }
        }
        nconf( x, y ) += sc0;

        if ( nconf( x, y ) & s ) {
          // make transition from sensitized to transmission or confluent state
          l = nconf( x, y );
          if ( (l & s) == s ) {
            nconf( x, y ) = CMASK;
          } else {
            // other leaves of the S-to-T-transition tree of depth 3
            l += s0;
            nconf( x, y ) = TMASK | ((l&s)<<6);
          }
        }
      }// else {
      // stay for another run
      //}
    }
  }

  else  {
    // this state is undefined!
  }
}
return_val = nCounter;
"""
        cconf = self.currConf
        nconf = self.nextConf
        sizeX = self.sizeX
        sizeY = self.sizeY
        cCounter = self.cCounter
        cList = self.cList
        nList = self.nList
        cActArr = self.cActArr
        nActArr = self.nActArr
        print "IN PY-1: cCounter", cCounter

        self.cCounter = weave.inline( vonNeumannCodeFewStates, [ 'cconf', 'nconf', 'sizeX', 'sizeY',
                                                                 'cList', 'nList', 'cCounter',
                                                                 'cActArr', 'nActArr' ],
                                      type_converters = converters.blitz,
                                      compiler = 'gcc' )
        self.currConf = self.nextConf.copy()
        self.cActArr, self.nActArr = self.nActArr.copy(), self.cActArr.copy()
        self.cList = self.nList
