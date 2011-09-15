try:
    from PySide.QtCore import *
    from PySide.QtGui import *
    from PySide.QtTest import *
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

if HAVE_QT:
    from zasim.gui.display import ZasimDisplay
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

    def test_start_stop_elementary_2d_base2(self):
        other_thread = QThread()
        sim_obj = cagen.ElementarySimulator((200, 200), rule=99, copy_borders=True, base=2)

        sim_obj.moveToThread(other_thread)

        display = ZasimDisplay(sim_obj)
        display.set_scale(2)

        other_thread.start()

        QTest.mouseClick(display.control.start_button, Qt.LeftButton)

        for execution in seconds(0.5):
            self.app.processEvents()
        assert not display.control.start_button.isVisible()
        for execution in seconds(0.5):
            self.app.processEvents()
        QTest.mouseClick(display.control.stop_button, Qt.LeftButton)
        for execution in seconds(0.5):
            self.app.processEvents()
        assert not display.control.stop_button.isVisible()
        for execution in seconds(0.5):
            self.app.processEvents()
