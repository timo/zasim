try:
    from PySide.QtCore import *
    from PySide.QtGui import *
    try:
        from PySide.QtOpenGL import *
    except ImportError:
        print "Using QWidget instead of QGlWidget"
        QGLWidget = QWidget
    print "using pyside"
except ImportError:
    # first, set QString and QVariant to api version 2, which causes them
    # to be created as normal python objects.
    import sip
    sip.setapi("QString", 2)
    sip.setapi("QVariant", 2)

    # now import all of pyqt.
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    try:
        from PyQt4.QtOpenGL import *
    except ImportError:
        print "Using QWidget instead of QGlWidget"
        QGLWidget = QWidget
    Signal = pyqtSignal
    print "using pyqt4"
