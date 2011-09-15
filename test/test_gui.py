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

import numpy as np

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
        sim_obj = cagen.ElementarySimulator(size, copy_borders=True, base=base, histogram=histogram)

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

    def test_reset_button(self):
        other_thread = QThread()
        sim_obj = cagen.ElementarySimulator((1000, 100), copy_borders=True, base=3)

        sim_obj.moveToThread(other_thread)

        display = ZasimDisplay(sim_obj)
        display.set_scale(1)

        QTest.qWaitForWindowShown(display.window)

        reset_button = display.control.findChild(QWidget, u"reset")

        display.control.zero_percentage.setValue(33)
        QTest.mouseClick(reset_button, Qt.LeftButton)

        config = sim_obj.get_config()
        histogram = np.bincount(config.ravel())
        zeros = histogram[0]
        other = sum(histogram[1:])
        assert abs((1.0 * zeros / (zeros + other)) - 0.33) < 0.2

        display.control.zero_percentage.setValue(99)
        QTest.mouseClick(reset_button, Qt.LeftButton)

        config = sim_obj.get_config()
        histogram = np.bincount(config.ravel())
        zeros = histogram[0]
        other = sum(histogram[1:])
        assert abs((1.0 * zeros / (zeros + other)) - 0.99) < 0.2

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
        calls = produce_more(calls, "base", [2, 3, 5])
    if "histogram" in metafunc.funcargnames:
        calls = produce_more(calls, "histogram", [False, True],
                lambda call: len(call["size"]) == 2)

    for call in calls:
        metafunc.addcall(funcargs=call)
