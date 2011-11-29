"""

"""
# This file is part of zasim. zasim is licensed under the BSD 3-clause license.
# See LICENSE.txt for details.

# Copyright (c) 2011, Felix Bondarenko

import numpy as np

## A map from states according to the bitmask to
# pygame blittable states ( between 0 and 28 )
displayableStateDict = {
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
nameStateDict = { "U": 0,
                  "C00" : 2048, "C10" : 2049, "C01" : 2050, "C11" : 2051,
                  "S"   : 4096, "S0"  : 4128, "S1"  : 4144, "S00" : 4160,
                  "S01" : 4168, "S10" : 4176, "S11" : 4184, "S000": 4192,
                  "T000": 6144, "T001": 6272, "T010": 6400, "T011": 6528,
                  "T020": 6656, "T032": 6784, "T030": 6912, "T031": 7040,
                  "T100": 7168, "T101": 7296, "T110": 7424, "T111": 7552,
                  "T120": 7680, "T121": 7808, "T130": 7936, "T131": 8064 }
stateNameDict = {a:b for b,a in nameStateDict.iteritems()}

## An array containing all correct states (see vonNeumann)
states = [ 0, 2048, 2049, 2050, 2051, 4096, 4128, 4144, 4160, 4168,
           4176, 4184, 4192, 6144, 6272, 6400, 6528, 6656, 6784,
           6912, 7040, 7168, 7296, 7424, 7552, 7680, 7808, 7936, 8064 ]

try:
    from ..external.qt import QImage, QPainter, QRect, QPixmap, QSize, QPen, Qt #, QPointF

    from os import path
    import math

    # compose a texture atlas from the images
    # additionally, create a dictionary of "factories" for QPixmapFragment objects

    # just get the size of the tiles
    size = QImage("images/vonNeumann/U.jpg").rect()
    one_w, one_h = size.width(), size.height()

    columns = int(math.ceil(math.sqrt(len(states))))
    rows = len(states) / columns

    new_image = QPixmap(QSize(columns * one_w, rows * one_h))
    PALETTE_JVN_PF = {}
    PALETTE_JVN_RECT = {}

    ptr = QPainter(new_image)
    for num, name in enumerate([stateNameDict[num] for num in states]):
        img = QImage(path.join("images/vonNeumann", name + ".jpg"))
        if img.isNull():
            print "warning:", name, "not found."
            img = QImage(one_w, one_h, QImage.Format_RGB32)
            img.fill(0xffff00ff)
            errptr = QPainter(img)
            errptr.setPen(QPen("white"))
            fnt = errptr.font()
            fnt.setPixelSize(42)
            errptr.setFont(fnt)
            errptr.drawText(QRect(0, 0, one_w, one_h), Qt.AlignCenter, u"ERROR\n%s not found\n:(" % (name))
            errptr.end()

        position_rect = QRect(one_w * (num / rows), one_h * (num % rows), one_w, one_h)
        ptr.drawImage(position_rect, img, img.rect())
        #PALETTE_JVN_PF[nameStateDict[name]] = lambda x, y: QPainter.PixmapFragment.create(
                #QPointF(x, y),
                #position_rect)
        PALETTE_JVN_RECT[nameStateDict[name]] = position_rect

    ptr.end()

    PALETTE_JVN_IMAGE = new_image

except ImportError:
    print "could not import qt for JVN CA palette"
    raise

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
class vonNeumann ( object ):
    palette = []
    ## The constructor
    def __init__( self, sizeX, sizeY, confFile ):
        ## The ca's title
        self.title = "vonNeumann"
        ## The ca's dimension
        self.dim = 2
        self.size = self.sizeX, self.sizeY = sizeX, sizeY


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
        self.displayConf = np.zeros( self.size, int )

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
