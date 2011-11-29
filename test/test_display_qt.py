try:
    from PySide.QtCore import *
    from PySide.QtGui import *
    from PySide.QtTest import *

    app = qApp or QApplication([])
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

if HAVE_QT:
    from zasim.display.qt import *
    from zasim.config import *
    from zasim.cagen import jvn

import pytest

import numpy as np

import sys
import signal
import traceback

_exceptions = []
def my_except_hook(cls, instance, traceback):
    print "oh god, an exception!"
    print cls
    print instance
    print traceback
    print
    traceback.print_exception(cls, instance, traceback)
    _exceptions.append((cls, instance, traceback))

_aborts = []
def my_abort_hook():
    print "oh god, sigabort!"
    print
    print traceback.print_stack()
    print
    _aborts.append(True)

def fail_on_exceptions():
    exc = _exceptions[:]
    [_exceptions.remove(a) for a in exc]
    aborts = _aborts[:]
    [_aborts.remove(a) for a in aborts]
    if exc:
        pytest.fail("There were exceptions in the base.\n%s" % (exc[0]))
    if aborts:
        pytest.fail("There were abort signals in the tests.")

def setup_module():
    sys.excepthook = my_except_hook
    signal.signal(signal.SIGABRT, my_abort_hook)

def teardown_module():
    sys.excepthook = sys.__excepthook__
    signal.signal(signal.SIGABRT, signal.SIG_DFL)

@pytest.mark.skipif("not HAVE_QT")
class TestDisplayQt:
    def test_tiled_display(self):
        test_conf = RandomInitialConfigurationFromPalette(jvn.states)
        conf = test_conf.generate((10, 10))

        img = render_state_array_tiled(conf)

        img2 = render_state_array_tiled(conf,region=(2, 2, 6, 6))
        img3 = render_state_array_tiled(conf,region=(2, 2, 6, 6), tilesize=32)
