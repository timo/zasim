from __future__ import print_function

import sys

try:
    from PySide.QtCore import *
    from PySide.QtGui import *
    print("using pyside", file=sys.stderr)
except ImportError:
    # first, set QString and QVariant to api version 2, which causes them
    # to be created as normal python objects.
    import sip
    sip.setapi("QString", 2)
    sip.setapi("QVariant", 2)

    # now import all of pyqt.
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    Signal = pyqtSignal
    print ("using pyqt4", file=sys.stderr)
