from __future__ import absolute_import
from zasim import ca, cagen
from random import randrange
from .testutil import *

import pytest

MIN_SIZE, MAX_SIZE = 5, 25

class TestCAGen:
    @pytest.mark.skipif("not ca.HAVE_WEAVE")
    def test_compare_weaves(self, rule_num):
        size = randrange(MIN_SIZE, MAX_SIZE)
        br = ca.binRule(rule_num, size, 1, ca.binRule.INIT_RAND)
        br2 = cagen.BinRule(size-2, rule=rule_num, config=br.getConf().copy()[1:-1])

        for i in range(10):
            br.updateAllCellsWeaveInline()
            br2.step_inline()
            compare_arrays(br.getConf(), br2.cconf)

        assert_arrays_equal(br.getConf(), br2.cconf)

    @pytest.mark.skipif("not ca.HAVE_WEAVE")
    def test_gen_weave_only(self, tested_rule_num):
        confs = TESTED_BINRULE[tested_rule_num]
        br = cagen.BinRule(rule=tested_rule_num, config=confs[0][1:-1])
        pretty_print_binrule(br.rule)
        assert_arrays_equal(br.cconf, confs[0])
        for conf in confs[1:]:
            br.step_inline()
            assert_arrays_equal(br.cconf, conf)

    def test_gen_pure_only(self, tested_rule_num):
        confs = TESTED_BINRULE[tested_rule_num]
        br = cagen.BinRule(rule=tested_rule_num, config=confs[0][1:-1])
        pretty_print_binrule(br.rule)
        assert_arrays_equal(br.cconf, confs[0])
        for conf in confs[1:]:
            br.step_pure_py()
            assert_arrays_equal(br.cconf, conf)

    def test_compare_pures(self, rule_num):
        size = randrange(MIN_SIZE, MAX_SIZE)
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
        size = randrange(MIN_SIZE, MAX_SIZE)
        br = cagen.BinRule(size-2, deterministic=False, rule=rule_num)

        for i in range(10):
            br.step_pure_py()

    @pytest.mark.skipif("not ca.HAVE_WEAVE")
    def test_run_nondeterministic_weave(self, rule_num):
        size = randrange(MIN_SIZE, MAX_SIZE)
        br = cagen.BinRule(size-2, deterministic=False, rule=rule_num)

        for i in range(10):
            br.step_inline()

    def test_immutability(self):
        br = cagen.BinRule(size=10)
        with pytest.raises(AssertionError):
            br.stepfunc.set_target(br)
        with pytest.raises(AttributeError):
            br.stepfunc.add_code("headers", "int foo = 42")
        with pytest.raises(AttributeError):
            br.stepfunc.add_py_hook("pre_compute", "print 'hello'")

def pytest_generate_tests(metafunc):
    if "rule_num" in metafunc.funcargnames:
        for i in INTERESTING_BINRULES:
            metafunc.addcall(funcargs=dict(rule_num=i))
    if "tested_rule_num" in metafunc.funcargnames:
        for i in TESTED_BINRULE.keys():
            metafunc.addcall(funcargs=dict(tested_rule_num=i))
