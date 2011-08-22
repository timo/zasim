from __future__ import absolute_import

"""This module offers a display and interaction frontend with Qt.

It will try importing PySide first, and if that fails PyQt. The code will
constantly be tested with both bindings."""

from .ca import binRule

try:
    from PySide.QtCore import *
    from PySide.QtGui import *
    print "using pyside"
except ImportError:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    print "using pyqt4"
import Queue
import sys
import random
import time

class PySideControl(QWidget):
    def __init__(self, simulator, parent=None):
        super(PySideControl, self).__init__(parent)

        self.sim = simulator
        self.timer_delay = 10
        self.attached_displays = []

        self.setup_ui()

    def setup_ui(self):
        l = QHBoxLayout(self)
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setDisabled(True)
        delay = QSpinBox()

        l.addWidget(self.start_button)
        l.addWidget(self.stop_button)
        l.addWidget(delay)
        self.setLayout(l)

        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        delay.valueChanged.connect(self.delay_changed)

    def start(self):
        self.timer_id = self.startTimer(self.timer_delay)
        self.start_button.setDisabled(True)
        self.stop_button.setEnabled(True)

    def stop(self):
        self.killTimer(self.timer_id)
        self.stop_button.setDisabled(True)
        self.start_button.setEnabled(True)

    def delay_changed(self, delay):
        self.timer_delay = int(delay)

    def timerEvent(self, event):
        self.killTimer(self.timer_id)
        self.step()
        self.timer_id = self.startTimer(self.timer_delay)

    def step(self):
        self.sim.step()
        for d in self.attached_displays:
            d.after_step()

    def attach_display(self, display):
        self.attached_displays.append(display)

    def detach_display(self, display):
        self.attached_displays.remove(display)

    def fullspeed(self):
        last_time = time.time()
        last_step = 0
        while self.isVisible():
            self.step()
            last_step += 1
            QApplication.processEvents()
            if last_step % 1000 == 1:
                diff, last_time = time.time() - last_time, time.time()
                print last_step, diff


class PySideDisplay(QWidget):
    def __init__(self, simulator, size, scale=1, parent=None):
        super(PySideDisplay, self).__init__(parent)
        self.sim = simulator
        self.scale = scale
        self.size = size
        self.width = self.sim.sizeX

        self.image = QBitmap(self.sim.sizeX, self.size)
        self.image.clear()

        self.display_queue = Queue.Queue(self.size)
        self.last_step = 0
        self.queued_steps = 0

        self.resize(self.sim.sizeX * self.scale,
                    self.size * self.scale)

        self.timer_delay = 10

    def paintEvent(self, ev):
        rendered = 0
        y = self.last_step % self.size
        paint = QPainter(self.image)
        try:
            while rendered < 100:
                conf = self.display_queue.get_nowait()
                self.queued_steps -= 1
                ones = []
                paint.setPen(Qt.color0)
                for x, field in enumerate(conf):
                    if field == 1:
                        ones.append(x)
                    else:
                        paint.drawPoint(x, y)
                paint.setPen(Qt.color1)
                for x in ones:
                    paint.drawPoint(x, y)
                rendered += 1
                self.last_step += 1
                y = self.last_step % self.size
        except Queue.Empty:
            pass

        copier = QPainter(self)
        copier.setPen(QColor("white"))
        copier.setBackground(QColor("black"))
        copier.setBackgroundMode(Qt.OpaqueMode)

        self._copy_pixmap(ev.rect(), copier)


    def _copy_pixmap(self, target, painter, damageRect=None):
        """_copy_pixmap(self, target, painter, damageRect)

        cleverly copies over a part of the stored image onto the widget.
        target is a the rect on the widget that's supposed to be updated,
        painter is the painter to be used for drawing,
        damageRect is an optional rect to limit the redrawing"""
        if damageRect:
            target = damageRect.intersected(target)
        if self.scale == 1:
            src = target
        else:
            target.setX(int(target.x() / self.scale) * self.scale)
            target.setY(int(target.y() / self.scale) * self.scale)
            target.setWidth(int(target.width() / self.scale) * self.scale + self.scale)
            target.setHeight(int(target.height() / self.scale) * self.scale + self.scale)
            src = QRect(target.x() / self.scale,
                        target.y() / self.scale,
                        target.width() / self.scale,
                        target.height() / self.scale)

        painter.drawPixmap(target, self.image, src)

    def after_step(self):
        conf = self.sim.getConf().copy()
        try:
            self.display_queue.put_nowait(conf)
        except Queue.Full:
            # the queue is initialised to hold as much lines as the
            # screen does. if we have more changes queued up than can
            # fit on the screen, we can just skip some of them.
            self.display_queue.get()
            self.display_queue.put(conf)
            # theoretically, in this case, the queued steps var would
            # have to be treated in a special way so that the update
            # line wanders around so that it still works, but
            # since the whole screen will get updated anyway, we
            # don't need to care at all.

        self.queued_steps += 1
        self.update(QRect(QPoint(0, ((self.last_step + self.queued_steps - 1) % self.size) * self.scale), QSize(self.width * self.scale, self.scale)))


def main():
    app = QApplication(sys.argv)

    scale = 2
    sizex, sizey = 800 / scale, 600 / scale

    # get a random beautiful CA
    sim = binRule(random.choice(
         [22, 26, 30, 45, 60, 73, 90, 105, 110, 122, 106, 150]),
         sizex, 0, binRule.INIT_RAND)
    disp = PySideDisplay(sim, sizey, scale)

    window = QMainWindow()


    central_widget = QWidget(window)

    window_l = QVBoxLayout(central_widget)

    scroller = QScrollArea()
    window_l.addWidget(scroller)
    scroller.setWidget(disp)
    scroller.resize(800, 600)

    control = PySideControl(sim, parent=central_widget)
    window_l.addWidget(control)
    control.attach_display(disp)

    window.setCentralWidget(central_widget)
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
