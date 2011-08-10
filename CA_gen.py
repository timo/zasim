from scipy import weave

class WeaveStepFuncVisitor(object):
    def visit(self, code):
        pass

class StateAccessor(object):
    def visit(self, code):
        pass

class CellLoop(object):
    def visit(self, code):
        pass

class WeaveStepFunc(object):
    def __init__(self):
        sections = "headers localvars loop_begin pre_compute compute post_compute loop_end after_step".split()
        self.code = dict((s, []) for s in sections)
        self.code_text = ""

        self.attrs = []

        self.acc = None

    def add_code(self, hook, code):
        self.code[hook].append(code)

    def regen_code(self):
        code_bits = []
        for section, bits in self.code.iteritems():
            code_bits.extend(bits)
        self.code_text = "\n".join(code_bits)

    def inline(self, target):
        weave.inline( self.code_text,
            local_dict=dict((k, getattr(target, k)) for k in self.attrs))

class LinearStateAccessor(StateAccessor):
    def read_access(self, pos):
        return "cconf(%s, 0)" % pos

    def write_access(self, pos):
        return "nconf(%s, 0)" % pos

class LinearCellLoop(CellLoop):
    def get_position(self):
        return "i"

    def visit(self, code):
        code.add_code("loop_begin",
                """for(int i=1; i < sizeX-1; i++) {""")
        code.add_code("loop_end",
                """}""")

class Neighbourhood(WeaveStepFuncVisitor):
    pass

class LinearNeighbourhood(Neighbourhood):
    def __init__(self, names, offsets):
        self.names = tuple(names)
        self.offsets = tuple(offsets)
        assert len(self.names) == len(self.offsets)

    def visit(self, code):
        for name, offset in zip(self.names, self.offsets):
            code.add_code("pre_compute",
                "%s = %s + %d" % (name,
                                  code.acc.read_access(code.loop.get_position()),
                                  offset))

    def neighbourhood_cells(self):
        return self.names

    def bounding_box(self):
        return min(self.offsets), max(self.offsets)
