try:
    from PySide.QtCore import *
    from PySide.QtGui import *
    from PySide.QtTest import *
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

if HAVE_QT:
    from zasim.gui.display import ZasimDisplay
    from zasim.gui.histogram import HistogramExtraDisplay
    from zasim.gui.animation import WaitAnimationWindow
    from zasim import cagen

import time
import pytest

import numpy as np

def seconds(num):
    end = time.time() + num
    while time.time() < end:
        yield 1

import sys
import signal
import traceback

_exceptions = []
def my_except_hook(cls, instance, traceback_o):
    print "oh god, an exception!"
    print cls
    print instance
    print traceback_o
    print
    traceback.print_exception(cls, instance, traceback_o)
    _exceptions.append((cls, instance, traceback_o))

_aborts = []
def my_abort_hook():
    print "oh god, sigabort!"
    print
    print traceback.print_stack()
    print
    _aborts.append(True)

def fail_on_exceptions():
    import traceback
    exc = _exceptions[:]
    [_exceptions.remove(a) for a in exc]
    aborts = _aborts[:]
    [_aborts.remove(a) for a in aborts]
    if exc:
        exceptiontext = []
        for exception in exc:
            exceptiontext.extend(traceback.format_exception(*exception))
        pytest.fail("There were exceptions in the base.\n%s" % "\n".join(exceptiontext))
    if aborts:
        pytest.fail("There were abort signals in the tests.")

def setup_module():
    sys.excepthook = my_except_hook
    signal.signal(signal.SIGABRT, my_abort_hook)

def teardown_module():
    sys.excepthook = sys.__excepthook__
    signal.signal(signal.SIGABRT, signal.SIG_DFL)

@pytest.mark.skipif("not HAVE_QT")
class TestGui:
    def setup_method(self, method):
        try:
            self.app = QApplication([])
        except RuntimeError:
            self.app = QCoreApplication.instance()
        self.app.setQuitOnLastWindowClosed(True)

    def teardown_method(self, method):
        self.app.closeAllWindows()
        self.app.quit()
        self.app.exit(0)
        del self.app

    def test_start_stop_binrule(self, size, base, scale, histogram):
        print size, base, scale, histogram
        sim_obj = cagen.ElementarySimulator(size, copy_borders=True, base=base, histogram=histogram)

        display = ZasimDisplay(sim_obj)
        display.set_scale(scale)

        if histogram:
            extra_hist = HistogramExtraDisplay(sim_obj, parent=display,
                        height=200, maximum=size[0] * size[1])
            extra_hist.show()
            display.window.attach_display(extra_hist)
            display.window.addDockWidget(Qt.RightDockWidgetArea, extra_hist)

        QTest.qWaitForWindowShown(display.window)

        QTest.mouseClick(display.control.start_button, Qt.LeftButton)

        for execution in seconds(0.1):
            self.app.processEvents()
        assert not display.control.start_button.isVisible()
        for execution in seconds(0.1):
            self.app.processEvents()
        QTest.mouseClick(display.control.stop_button, Qt.LeftButton)
        for execution in seconds(0.1):
            self.app.processEvents()
        assert not display.control.stop_button.isVisible()

        self.app.closeAllWindows()
        fail_on_exceptions()

    def find_message_box(self, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            widgets = self.app.allWidgets()
            for widget in widgets:
                if isinstance(widget, QMessageBox):
                    return widget
            self.app.processEvents()

    def test_elementary_gui(self, base):
        sim_obj = cagen.ElementarySimulator((10, 10), copy_borders=True, base=base)

        display = ZasimDisplay(sim_obj)
        display.set_scale(1)

        QTest.qWaitForWindowShown(display.window)

        menu = display.window.menuBar().findChild(QMenu, u"simulator_menu")
        assert menu is not None
        QTest.mouseClick(menu, Qt.LeftButton)

        elementary_action = menu.findChild(QAction, u"stepfunc_table")
        elementary_action.trigger()

        for execution in seconds(0.1):
            self.app.processEvents()

        elementary_window = self.app.activeWindow()
        assert elementary_window is not None

        actions = [act for act in elementary_window.findChildren(QPushButton)
                    if act is not None and act.objectName().startswith("action_")]

        for action in actions:
            QTest.mouseClick(action, Qt.LeftButton)
            for execution in seconds(0.1):
                self.app.processEvents()

        self.app.closeAllWindows()

        fail_on_exceptions()

        #minimize = elementary_window.findChild(QPushButton, u"minimize")

        #print "clicking now"
        #class foo(QThread):
            #def run(self):
                #QTest.mouseClick(minimize, Qt.LeftButton)
        #t = foo()
        #t.start()

        #popup = self.find_message_box()
        #popup.close()

    def test_animation(self):
        anim = WaitAnimationWindow()

        for execution in seconds(1):
            self.app.processEvents()

        fail_on_exceptions()

def produce_more(calls, arg, values, filter_func=lambda call: True):
    """Add, to all `calls`, a call for each `value` for the `arg`, so that
    all combinations will exist in the returned list.

    If calls is empty, generate a dict for each value as the result.

    If the filter_func is supplied, every old call will be passed to it and,
    if the filter_func returns True, new calls will be produced based on the
    values supplied. If the filter_func returns False, only the first value
    will be set on the old call.
    """
    if not calls:
        return [{arg: value} for value in values]

    ncalls = []
    for call in calls:
        if filter_func(call):
            values_to_use = values
        else:
            values_to_use = values[:1]
        for value in values_to_use:
            new_call = call.copy()
            new_call[arg] = value
            ncalls.append(new_call)

    return ncalls

def pytest_generate_tests(metafunc):
    calls = []
    if "scale" in metafunc.funcargnames:
        calls = produce_more(calls, "scale", [1, 4])
    if "size" in metafunc.funcargnames:
        calls = produce_more(calls, "size", [(100,), (100, 100)])
    if "base" in metafunc.funcargnames:
        calls = produce_more(calls, "base", [2, 3])
    if "histogram" in metafunc.funcargnames:
        calls = produce_more(calls, "histogram", [False, True],
                lambda call: len(call["size"]) == 2)

    for call in calls:
        metafunc.addcall(funcargs=call)
