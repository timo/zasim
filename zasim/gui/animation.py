from ..external.qt import *

class WaitAnimationWindow(QObject):
    """Display a cute animation, so that the user isn't annoyed by those long,
    long compile times of weave.inline."""
    def __init__(self, **kwargs):
        super(WaitAnimationWindow, self).__init__(**kwargs)

        import pkg_resources as pkg

        scene = QGraphicsScene()

        snake_img = pkg.resource_filename("zasim", "idle.png")
        snake_pic = QImage(snake_img)
        cut_x = 75
        left_part = QPixmap(snake_pic.copy(QRect(QPoint(0, 0), QSize(cut_x, 175))))
        right_part = QPixmap(snake_pic.copy(QRect(QPoint(cut_x, 0), QPoint(175, 175))))

        snake_pos_x = -100
        snake_pos_y = -80
        l_snake = scene.addPixmap(left_part)
        l_snake.setPos(QPoint(snake_pos_x, snake_pos_y))

        numbers_offset = -10

        self.gv = QGraphicsView(scene)
        self.gv.setFixedSize(150, 150)
        self.gv.setSceneRect(QRectF(-75, -75, 150, 150))
        self.gv.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.gv.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        bits = []
        bit_count = 30
        for bit in range(bit_count):
            bitFont = QFont("Monospace", random.randint(8, 16), QFont.Bold, random.choice([True, False]))
            bitBit = QGraphicsTextItem(random.choice("01"))
            bitBit.setFont(bitFont)
            scene.addItem(bitBit)
            x_duration = random.randint(6000, 8000)
            x_anim = QGraphicsItemAnimation()
            x_anim = QPropertyAnimation(bitBit, QByteArray("x"), bitBit)
            x_anim.setDuration(x_duration)
            x_anim.setStartValue(150)
            x_anim.setEndValue(-150)
            x_anim.setLoopCount(-1)
            up_down_duration = random.randint(800, 1200)
            up_down = random.randint(10, 20)
            up_anim = QPropertyAnimation(bitBit, QByteArray("y"), bitBit)
            up_anim.setDuration(up_down_duration)
            up_anim.setStartValue(-up_down + numbers_offset)
            up_anim.setEndValue(up_down + numbers_offset)
            down_anim = QPropertyAnimation(bitBit, QByteArray("y"), bitBit)
            down_anim.setDuration(up_down_duration)
            down_anim.setStartValue(up_down + numbers_offset)
            down_anim.setEndValue(-up_down + numbers_offset)
            up_down_anim = QSequentialAnimationGroup(bitBit)
            up_down_anim.addAnimation(up_anim)
            up_down_anim.addAnimation(down_anim)
            up_down_anim.setLoopCount(-1)

            up_down_anim.start()
            x_anim.start()

            x_anim.setCurrentTime(random.randint(0, x_duration))
            up_down_anim.setCurrentTime(random.randint(0, up_down_duration))

        r_snake = scene.addPixmap(right_part)
        r_snake.setPos(QPoint(snake_pos_x + cut_x, snake_pos_y))

        ct = scene.addSimpleText("Compiling")
        ct.setFont(QFont("Monospace", 12))
        ct.translate(-ct.boundingRect().width()/2., 75 - ct.boundingRect().height())

        self.gv.centerOn(0, 0)

        self.scene = scene
        self.gv.show()

    def destroy(self):
        self.gv.deleteLater()
