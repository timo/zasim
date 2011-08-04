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

        self.image = QPixmap(self.sim.sizeX, self.size)

        self.display_queue = Queue.Queue()
        self.last_step = 0
        self.queued_steps = 0

        self.resize(self.sim.sizeX * self.scale,
                    self.size * self.scale)

        self.startTimer(1)

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
                paint.setPen(QColor("black"))
                for x, field in enumerate(conf):
                    if field == 1:
                        ones.append(x)
                    else:
                        paint.drawPoint(x, y)
                paint.setPen(QColor("white"))
                for x in ones:
                    paint.drawPoint(x, y)
                rendered += 1
                self.last_step += 1
                y = self.last_step % self.size
        except Queue.Empty:
            pass

        copier = QPainter(self)
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
        self.display_queue.put(self.sim.getConf().copy())
        self.queued_steps += 1
        self.update(QRect(QPoint(0, ((self.last_step % self.size) + self.queued_steps - 1) * self.scale), QSize(self.width * self.scale, self.scale)))

    def timerEvent(self, event):
        self.step()

def main():
    app = QApplication(sys.argv)

    sim = binRule(random.randint(0, 256), 800, 0, binRule.INIT_RAND)
    disp = PySideDisplay(sim, 600, 3)

    window = QMainWindow()
    scroller = QScrollArea()
    scroller.setWidget(disp)
    window.setCentralWidget(scroller)
    scroller.resize(800, 600)

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
