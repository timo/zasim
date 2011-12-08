from __future__ import print_function
from . import WANT_GUI

import sys

import os

ZASIM_QT = os.environ.get("ZASIM_QT", "PySide").lower()

try:
    if ZASIM_QT != "pyside":
        raise ImportError("Use PyQt instead")

    from PySide.QtCore import *
    from PySide.QtGui import *
except ImportError:
    if ZASIM_QT != "pyqt":
        raise ImportError("Don't use PyQt.")
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

import os
app = None
if "DISPLAY" in os.environ and os.environ["DISPLAY"]:
    import sys
    if WANT_GUI:
        app = QApplication(sys.argv)
if app is None:
    app = QApplication(sys.argv, False)
