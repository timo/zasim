"""This module implements whatever's necessary to work with .zac files
like text_to_cell outputs."""

import yaml

n2c = lambda name: (int(name[1:name.find("l")]), int(name[name.find("l")+1:]))
n2c.__doc__ = """Turn a name of a subcell into x/y coords"""
c2n = lambda x, y: "c%dl%d" % (x, y)


def draw_box_template(boxes, w=1):
    """
    Create an ascii art template suitable for string interpolation.

    :param boxes: a list of x, y tuples that show which fields are filled.
    :param w: the width of each of the boxes.
    :returns: a list of strings usable for drawing an ascii box art."""

    w = max([t[0] for t in boxes])
    h = max([t[1] for t in boxes])

    template = ["" for _ in range(h * 2 + 3)]
    for x in range(w+1):
        for y in range(h+1):
            if (x, y) in boxes:
                template[y * 2] += "+--" + "-" * w
                template[y * 2 + 1] += "|%%(%s) %ds" % (c2n(x, y), w + 2)
            else:
                if (x, y-1) in boxes or (x - 1, y) in boxes or (x-1,y-1) in boxes:
                    template[y * 2] += "+"
                else:
                    template[y * 2] += " "
                if (x, y-1) in boxes:
                    template[y * 2] += "--" + "-" * w
                else:
                    template[y * 2] += "  " + " " * w
                if (x-1,y) in boxes:
                    template[y * 2 + 1] += "|"
                else:
                    template[y * 2 + 1] += " "
                template[y * 2 + 1] += "  " + " " * w

    for y in range(h+1):
        if (w,y) in boxes or (x, y-1) in boxes:
            template[y * 2] += "+"
        else:
            template[y * 2] += " "
        if (w,y) in boxes:
            template[y * 2 + 1] += "|"

    for x in range(w+1):
        if (x, h) in boxes or (x-1,h) in boxes:
            template[h * 2 + 2] += "+"
        else:
            template[h * 2 + 2] += " "
        if (x, h) in boxes:
            template[h * 2 + 2] += "--" + "-" * w
        else:
            template[h * 2 + 2] += "  " + " " * w

    return template

class ZacConsoleDisplay(object):
    def __init__(self, simulator, sets, strings, connect=True, auto_output=True):
        self._sim = simulator
        self._data = []
        self._last_conf = None
        self._auto_output = auto_output
        self.sets = sets
        self.strings = strings

        self.measure_sets()

        if connect:
            self.connect_simulator()

    def connect_simulator(self):
        self._sim.changed.connect(self.conf_changed)
        self._sim.updated.connect(self.after_step)
        self._sim.snapshot_restored.connect(self.conf_replaced)

    def after_step(self, update_step=True):
        self._last_conf = self._sim.get_config().copy()
        self.draw_conf(update_step)
        if self._auto_output:
            print str(self),

    def conf_changed(self):
        self.after_step(False)

    def conf_replaced(self):
        self.conf_changed()

    def measure_sets(self):
        self.set_sizes = {}
        for coord, contents in self.sets:
            self.set_sizes[coord] = 1 + max(map(len, map(str, contents))) + 1

    def draw_conf(self, update_step=True):
        pass

class ZacSimulator(object):
    def __init__(self, data_or_file):
        if isinstance(data_or_file, file):
            data = yaml.load(data_or_file)
        else:
            data = yaml.loads(data_or_file)

        self.sets = data.sets
        self.strings = data.strings
        self.python_code = data.python_code
        self.cpp_code = data.cpp_code

