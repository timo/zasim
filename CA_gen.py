from scipy import weave

class WeaveStepFuncVisitor(object):
    def visit(self, code):
        pass

class StateAccessor(WeaveStepFuncVisitor):
    pass

class CellLoop(WeaveStepFuncVisitor):
    pass

class Neighbourhood(WeaveStepFuncVisitor):
    pass

class BorderHandler(WeaveStepFuncVisitor):
    pass

class WeaveStepFunc(object):
    def __init__(self, loop, accessor, neighbourhood, extra_code=[]):
        self.sections = "headers localvars loop_begin pre_compute compute post_compute loop_end after_step".split()
        self.code = dict((s, []) for s in self.sections)
        self.code_text = ""

        self.attrs = []

        self.acc = accessor
        self.neigh = neighbourhood
        self.loop = loop

        self.acc.visit(self)
        self.neigh.visit(self)
        self.loop.visit(self)

    def add_code(self, hook, code):
        self.code[hook].append(code)

    def regen_code(self):
        code_bits = []
        for section in self.sections:
            code_bits.extend(self.code[section])
        self.code_text = "\n".join(code_bits)

    def inline(self, target):
        weave.inline( self.code_text,
            local_dict=dict((k, getattr(target, k)) for k in self.attrs))

class LinearStateAccessor(StateAccessor):
    def read_access(self, pos):
        return "cconf(%s, 0)" % pos

    def write_access(self, pos):
        return "nconf(%s, 0)" % pos

    def visit(self, code):
        code.add_code("localvars",
                """int result;""")
        code.add_code("post_compute",
                self.write_access(code.loop.get_position()) + " = result")

class LinearCellLoop(CellLoop):
    def get_position(self, offset=0):
        if offset != 0:
            return "i"
        else:
            return "i + %d" % (offset)

    def visit(self, code):
        code.add_code("loop_begin",
                """for(int i=1; i < sizeX-1; i++) {""")
        code.add_code("loop_end",
                """}""")

class LinearNeighbourhood(Neighbourhood):
    def __init__(self, names, offsets):
        self.names = tuple(names)
        self.offsets = tuple(offsets)
        assert len(self.names) == len(self.offsets)

    def visit(self, code):
        for name, offset in zip(self.names, self.offsets):
            code.add_code("pre_compute",
                "%s = %s" % (name,
                             code.acc.read_access(code.loop.get_position(offset))))

    def neighbourhood_cells(self):
        return self.names

    def bounding_box(self):
        return min(self.offsets), max(self.offsets)

class LinearBorderCopier(BorderHandler):
    def visit(self, code):
        code.add_code("after_step",
                code.acc.write_access("0") + " = " + code.acc.write_access("sizeX - 2") + ";\n" +
                code.acc.write_access("sizeX - 1") + " = " + code.acc.write_access("1") + ";")


def test():
    binRuleTestCode = WeaveStepFunc(
            loop=LinearCellLoop(),
            accessor=LinearStateAccessor(),
            neighbourhood=LinearNeighbourhood(["l", "m", "r"], (-1, 0, 1)))
    LinearBorderCopier().visit(binRuleTestCode)
    binRuleTestCode.attrs += "rule"
    binRuleTestCode.add_code("localvars",
            """int state;""")
    binRuleTestCode.add_code("compute",
            """state =  l << 2;
  state += m << 1;
  state += r;
  result = rule(state);""")
    binRuleTestCode.regen_code()
    print binRuleTestCode.code_text

if __name__ == "__main__":
    test()
