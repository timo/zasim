# <nbformat>2</nbformat>

# <codecell>
from __future__ import division

from zasim.config import *
from zasim.external.qt import *
from zasim.display.qt import PALETTE_32

_last_rendered_state_conf = None
def render_state_array(states, palette=PALETTE_32, invert=False, region=None):
    global _last_rendered_state_conf
    if region:
        x, y, w, h = region
        conf = states[x:x+w, y:y+h]
    else:
        x, y = 0, 0
        w, h = states.shape
        conf = states
    nconf = np.empty((w - x, h - y), np.uint32, "F")

    if not invert:
        nconf[conf==0] = palette[0]
        nconf[conf==1] = palette[1]
    else:
        nconf[conf==1] = palette[0]
        nconf[conf==0] = palette[1]

    for num, value in enumerate(palette[2:]):
        nconf[conf == num+2] = value

    image = QImage(nconf.data, w - x, h - y, QImage.Format_RGB32)

    # without this cheap trick, the data from the array is imemdiately freed and
    # subsequently re-used, leading to the first pixels in the top left corner
    # getting pretty colors and zasim eventually crashing.
    _last_rendered_state_conf = nconf
    return image

def qimage_to_pngstr(image):
    buf = QBuffer()
    buf.open(QIODevice.ReadWrite)
    image.save(buf, "PNG")
    buf.close()
    return str(buf.data())

# <codecell>
@function_of_radius
def bobbel_in_der_mitte(r, mr):
    return mr / (r + 0.1)

ones = bobbel_in_der_mitte
a = DensityDistributedConfiguration({0:(lambda x, y, w, h: 10), 1:ones})

# <codecell>

confs = [a.generate((100,100)) for num in xrange(50)]

for num, conf in enumerate(confs):
    qi = render_state_array(conf)
    qi.save("%05d.png" % (num))

