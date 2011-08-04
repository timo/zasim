from CA import binRule
from PySide.QtCore import *
from PySide.QtGui import *
import Queue
import sys
import random
import time

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
        if self.display_queue.empty():
            self.step()
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

    def step(self):
        self.sim.loopFunc()
        conf = self.sim.getConf().copy()
        try:
            self.display_queue.put(conf)
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

    def start(self):
        self.timer_id = self.startTimer(self.timer_delay)

    def stop(self):
        self.killTimer(self.timer_id)

    def timerEvent(self, event):
        self.killTimer(self.timer_id)
        self.step()
        self.timer_id = self.startTimer(self.timer_delay)

    def fullspeed(self):
        last_time = time.time()
        while True:
            self.step()
            QApplication.processEvents()
            if self.last_step % 1000 == 0:
                diff, last_time = time.time() - last_time, time.time()
                print self.last_step, diff

def main():
    app = QApplication(sys.argv)

    # get a random beautiful CA
    sim = binRule(random.choice(
         [22, 26, 30, 45, 60, 73, 90, 105, 110, 122, 106, 150]),
         400, 0, binRule.INIT_RAND)
    disp = PySideDisplay(sim, 300, 2)

    window = QMainWindow()
    scroller = QScrollArea()
    scroller.setWidget(disp)
    window.setCentralWidget(scroller)
    scroller.resize(800, 600)

    window.show()
    disp.fullspeed()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
