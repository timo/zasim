from CA import binRule
from PySide.QtCore import *
from PySide.QtGui import *
import Queue
import sys
import random

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
        self.timer_id = self.startTimer(self.timer_delay)

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
        if self.scale == 1:
            tgt = ev.rect()
            src = ev.rect()
        else:
            tgt = ev.rect()
            tgt.setX(int(tgt.x() / self.scale) * self.scale)
            tgt.setY(int(tgt.y() / self.scale) * self.scale)
            tgt.setWidth(int(tgt.width() / self.scale) * self.scale + self.scale)
            tgt.setHeight(int(tgt.height() / self.scale) * self.scale + self.scale)
            src = QRect(tgt.x() / self.scale,
                        tgt.y() / self.scale,
                        tgt.width() / self.scale,
                        tgt.height() / self.scale)
        copier.drawPixmap(tgt, self.image, src)

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

    def timerEvent(self, event):
        self.killTimer(self.timer_id)
        self.step()
        self.timer_id = self.startTimer(self.timer_delay)

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
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
