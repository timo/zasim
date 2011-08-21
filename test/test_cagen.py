from zasim import ca, cagen
from random import randrange
from testutil import assert_arrays_equal, compare_arrays

import pytest

class TestCAGen:
    @pytest.mark.skipif("not ca.HAVE_WEAVE")
    def test_compare_weaves(self, ruleNum):
        size = randrange(10, 30)
        br = ca.binRule(ruleNum, size, 1, ca.binRule.INIT_RAND)
        br2 = cagen.TestTarget(size-2, rule=ruleNum, config=br.getConf().copy()[1:-1])

        binRuleTestCode = cagen.WeaveStepFunc(
                loop=cagen.LinearCellLoop(),
                accessor=cagen.LinearStateAccessor(size=size-2),
                neighbourhood=cagen.LinearNeighbourhood(list("lmr"), (-1, 0, 1)),
                extra_code=[cagen.LinearBorderCopier()])

        binRuleTestCode.attrs.append("rule")
        binRuleTestCode.add_code("localvars",
                """int state;""")
        binRuleTestCode.add_code("compute",
                """state =  l << 2;
      state += m << 1;
      state += r;
      result = rule(state);""")

        binRuleTestCode.set_target(br2)
        binRuleTestCode.regen_code()

        for i in range(10):
            br.updateAllCellsWeaveInline()
            binRuleTestCode.step_inline()
            compare_arrays(br.getConf(), br2.cconf)

        assert_arrays_equal(br.getConf(), br2.cconf)

    def test_compare_pures(self, ruleNum):
        size = randrange(10, 30)
        br = ca.binRule(ruleNum, size, 1, ca.binRule.INIT_RAND)
        br2 = cagen.TestTarget(size-2, rule=ruleNum, config=br.getConf().copy()[1:-1])

        binRuleTestCode = cagen.WeaveStepFunc(
                loop=cagen.LinearCellLoop(),
                accessor=cagen.LinearStateAccessor(size=size-2),
                neighbourhood=cagen.LinearNeighbourhood(list("lmr"), (-1, 0, 1)),
                extra_code=[cagen.LinearBorderCopier()])

        binRuleTestCode.attrs.append("rule")

        binRuleTestCode.add_py_hook("compute",
                lambda state: dict(result=state["rule"][int(state["l"] * 4 + state["m"] * 2 + state["r"])]))

        binRuleTestCode.set_target(br2)
        binRuleTestCode.regen_code()

        for i in range(10):
            br.updateAllCellsPy()
            binRuleTestCode.step_pure_py()
            compare_arrays(br.getConf(), br2.cconf)

        assert_arrays_equal(br.getConf(), br2.cconf)

def pytest_generate_tests(metafunc):
    if "ruleNum" in metafunc.funcargnames:
        for i in range(128):
            metafunc.addcall(funcargs=dict(ruleNum=i))
