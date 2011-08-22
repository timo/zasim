from zasim import ca, cagen
from random import randrange
from testutil import *

import pytest

class TestCAGen:
    @pytest.mark.skipif("not ca.HAVE_WEAVE")
    def test_compare_weaves(self, rule_num):
        size = randrange(10, 30)
        br = ca.binRule(rule_num, size, 1, ca.binRule.INIT_RAND)
        br2 = cagen.BinRule(size-2, rule=rule_num, config=br.getConf().copy()[1:-1])

        for i in range(10):
            br.updateAllCellsWeaveInline()
            br2.step_inline()
            compare_arrays(br.getConf(), br2.cconf)

        assert_arrays_equal(br.getConf(), br2.cconf)

    def test_compare_pures(self, rule_num):
        size = randrange(10, 30)
        br = ca.binRule(rule_num, size, 1, ca.binRule.INIT_RAND)
        br2 = cagen.BinRule(size-2, rule=rule_num, config=br.getConf().copy()[1:-1])

        # are the rules the same?
        assert_arrays_equal(br.ruleIdx, br2.rule)

        assert_arrays_equal(br.getConf(), br2.cconf)

        for i in range(10):
            br.updateAllCellsPy()
            br2.step_pure_py()
            compare_arrays(br.getConf(), br2.cconf)

        assert_arrays_equal(br.getConf(), br2.cconf)

    def test_run_nondeterministic_pure(self, rule_num):
        size = randrange(10, 30)
        br = cagen.BinRule(size-2, deterministic=False, rule=rule_num)

        for i in range(10):
            br.step_inline()

    @pytest.mark.skipif("not ca.HAVE_WEAVE")
    def test_run_nondeterministic_weave(self, rule_num):
        size = randrange(10, 30)
        br = cagen.BinRule(size-2, deterministic=False, rule=rule_num)

        for i in range(10):
            br.step_pure_py()

def pytest_generate_tests(metafunc):
    if "rule_num" in metafunc.funcargnames:
        for i in INTERESTING_BINRULES:
            metafunc.addcall(funcargs=dict(rule_num=i))
