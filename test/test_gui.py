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
    from zasim import cagen

import time
import pytest

def seconds(num):
    end = time.time() + num
    while time.time() < end:
        yield 1

@pytest.mark.skipif("not HAVE_QT")
class TestGui:
    def setup_class(cls):
        """craetes a QT app and a socket spy"""
        cls.app = QApplication(["test"])
        cls.app.setApplicationName("zasim gui test")

    def test_start_stop_elementary(self, size, base, scale, histogram):
        other_thread = QThread()
        sim_obj = cagen.ElementarySimulator(size, rule=99, copy_borders=True, base=base)

        sim_obj.moveToThread(other_thread)

        display = ZasimDisplay(sim_obj)
        display.set_scale(scale)

        if histogram:
            extra_hist = HistogramExtraDisplay(sim_obj, parent=display,
                        height=200, maximum=size[0] * size[1])
            extra_hist.show()
            display.window.attach_display(extra_hist)
            display.window.addDockWidget(Qt.RightDockWidgetArea, extra_hist)

        other_thread.start()

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
        for execution in seconds(0.1):
            self.app.processEvents()

def produce_more(calls, arg, values):
    """Add, to all `calls`, a call for each `value` for the `arg`, so that
    all combinations will exist in the returned list.

    If calls is empty, generate a dict for each value as the result."""
    if not calls:
        return [{arg: value} for value in values]

    ncalls = []
    for call in calls:
        for value in values:
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
        calls = produce_more(calls, "base", [2, 3, 5])
    if "histogram" in metafunc.funcargnames:
        calls = produce_more(calls, "histogram", [True, False])

    for call in calls:
        metafunc.addcall(funcargs=call)
